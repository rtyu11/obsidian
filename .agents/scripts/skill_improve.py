#!/usr/bin/env python3
"""
skill_improve.py
蓄積されたログをもとにスキルの問題点を分析し、SKILL.md の改善案を生成する。

使い方:
  python .agents/scripts/skill_improve.py --skill line_inbox   # 特定スキルを分析
  python .agents/scripts/skill_improve.py --all                # 全スキルを分析
  python .agents/scripts/skill_improve.py --skill line_inbox --apply  # 確認後に適用

環境変数:
  GEMINI_API_KEY  Google AI Studio で取得したAPIキー
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ローカル版 cognee (0.5.4.dev2) のパスを優先追加
LOCAL_COGNEE_ROOT = Path(__file__).parent.parent / "cognee" / "cognee-0.5.4.dev2"
if LOCAL_COGNEE_ROOT.exists():
    sys.path.insert(0, str(LOCAL_COGNEE_ROOT))
    # パッケージ本体 (cognee フォルダ) もインポート可能にする
    sys.path.insert(0, str(LOCAL_COGNEE_ROOT / "cognee"))

VAULT_PATH = Path(__file__).parent.parent.parent
SKILLS_FOLDER = VAULT_PATH / ".agents" / "skills"
LOG_FILE = VAULT_PATH / ".agents" / "logs" / "skill_runs.jsonl"
IMPROVE_LOG = VAULT_PATH / ".agents" / "logs" / "skill_improvements.jsonl"


def setup_env():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: 環境変数 GEMINI_API_KEY が設定されていません。")
        sys.exit(1)
    os.environ.setdefault("LLM_PROVIDER", "gemini")
    os.environ.setdefault("LLM_MODEL", "gemini-3-flash-preview")
    os.environ.setdefault("LLM_API_KEY", api_key)
    os.environ.setdefault("EMBEDDING_PROVIDER", "gemini")
    os.environ.setdefault("EMBEDDING_MODEL", "text-embedding-004")
    os.environ.setdefault("EMBEDDING_API_KEY", api_key)

    # 接続テストをバイパス（恒久的なタイムアウト回避設定）
    os.environ["COGNEE_SKIP_CONNECTION_TEST"] = "true"
    db_path = VAULT_PATH / ".agents" / "cognee" / "db"
    db_path.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DB_PATH", str(db_path))
    return api_key


def load_logs(skill_name: str = None) -> dict:
    """ログファイルからスキルごとの実行履歴を読み込む"""
    if not LOG_FILE.exists():
        return {}

    runs_by_skill = defaultdict(list)
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                runs_by_skill[entry["skill"]].append(entry)
            except json.JSONDecodeError:
                continue

    if skill_name:
        return {skill_name: runs_by_skill.get(skill_name, [])}
    return dict(runs_by_skill)


def get_skill_path(skill_name: str) -> Path:
    return SKILLS_FOLDER / skill_name / "SKILL.md"


def analyze_runs(runs: list) -> dict:
    """実行履歴を統計分析"""
    if not runs:
        return {"count": 0, "avg_score": None, "failures": []}

    scores = [r["score"] for r in runs]
    avg = sum(scores) / len(scores)
    failures = [r for r in runs if r["score"] < 0.5]

    return {
        "count": len(runs),
        "avg_score": round(avg, 2),
        "failures": failures,
        "recent_runs": runs[-5:],  # 直近5件
    }


async def generate_improvement(skill_name: str, skill_content: str,
                                analysis: dict, api_key: str) -> str:
    """Gemini API でスキルの改善案を生成"""
    try:
        from google import genai
    except ImportError:
        print("ERROR: google-genai がインストールされていません。")
        sys.exit(1)

    failures_text = ""
    if analysis["failures"]:
        failures_text = "\n".join([
            f"- タスク: {f['task']} / スコア: {f['score']} / 結果: {f['summary']}"
            for f in analysis["failures"][-5:]
        ])
    else:
        failures_text = "（失敗記録なし）"

    recent_text = "\n".join([
        f"- [{r['timestamp'][:10]}] score={r['score']} | {r['task']} → {r['summary']}"
        for r in analysis["recent_runs"]
    ]) if analysis["recent_runs"] else "（実行記録なし）"

    prompt = f"""
あなたはObsidian Vaultで使われるAIエージェントのスキル改善専門家です。
以下のスキル「{skill_name}」の実行履歴を分析し、SKILL.md の改善案を提案してください。

## 現在の SKILL.md
```markdown
{skill_content}
```

## 実行統計
- 実行回数: {analysis['count']}
- 平均成功スコア: {analysis['avg_score']}

## 直近の実行ログ
{recent_text}

## 失敗ケース
{failures_text}

## タスク
1. 失敗の原因を3点以内で簡潔に分析する
2. SKILL.md の改善案を提案する（変更が必要な箇所のみ、差分形式で）
3. 改善の期待効果を説明する

日本語で回答してください。
"""

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    return response.text.strip()


def apply_improvement(skill_name: str, new_content: str):
    """SKILL.md を更新し、バックアップを保存"""
    skill_path = get_skill_path(skill_name)
    if not skill_path.exists():
        print(f"ERROR: {skill_path} が存在しません。")
        return False

    # バックアップ
    backup_dir = VAULT_PATH / ".agents" / "cognee" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{skill_name}_SKILL_{timestamp}.md.bak"
    backup_path.write_text(skill_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  バックアップ: {backup_path.relative_to(VAULT_PATH)}")

    # 更新
    skill_path.write_text(new_content, encoding="utf-8")
    print(f"  ✅ {skill_name}/SKILL.md を更新しました。")

    # 改善ログ
    IMPROVE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(IMPROVE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "skill": skill_name,
            "backup": str(backup_path),
        }, ensure_ascii=False) + "\n")

    return True


async def improve_skill(skill_name: str, auto_apply: bool, api_key: str):
    """単一スキルの分析と改善"""
    print(f"\n{'='*50}")
    print(f"スキル分析: {skill_name}")
    print('='*50)

    skill_path = get_skill_path(skill_name)
    if not skill_path.exists():
        print(f"  ⚠️  SKILL.md が見つかりません: {skill_path.relative_to(VAULT_PATH)}")
        return

    skill_content = skill_path.read_text(encoding="utf-8")
    logs = load_logs(skill_name)
    runs = logs.get(skill_name, [])
    analysis = analyze_runs(runs)

    print(f"  実行記録: {analysis['count']} 件")
    if analysis['avg_score'] is not None:
        print(f"  平均スコア: {analysis['avg_score']}")
        if analysis['avg_score'] >= 0.8:
            print(f"  ✅ 良好なパフォーマンス")
        elif analysis['avg_score'] >= 0.5:
            print(f"  ⚠️  改善の余地あり")
        else:
            print(f"  ❌ 改善が必要")

    if analysis['count'] == 0:
        print("  実行記録がありません。まず skill_observe.py でログを記録してください。")
        return

    print("\n  Gemini で改善案を生成中...")
    improvement = await generate_improvement(skill_name, skill_content, analysis, api_key)

    print(f"\n{'─'*50}")
    print("【改善案】")
    print('─'*50)
    print(improvement)
    print('─'*50)

    if auto_apply:
        # 改善案をそのまま適用（プロダクションでは慎重に）
        print("\n⚠️  自動適用モードは現在サポートされていません。")
        print("  改善提案を確認して、手動で SKILL.md を編集してください。")
    else:
        print("\nSKILL.md を手動で編集してください。")
        print(f"  ファイル: {skill_path.relative_to(VAULT_PATH)}")
        print("\n改善完了後は以下を実行してグラフを更新:")
        print(f"  python .agents/scripts/skill_ingest.py --upsert")


async def main_async(args):
    api_key = setup_env()
    logs = load_logs()

    if args.all:
        # 全スキルを処理
        all_skills = [d.name for d in SKILLS_FOLDER.iterdir()
                      if d.is_dir() and (d / "SKILL.md").exists()]
        print(f"対象スキル: {len(all_skills)} 件")
        for skill_name in all_skills:
            await improve_skill(skill_name, args.apply, api_key)
    elif args.skill:
        await improve_skill(args.skill, args.apply, api_key)
    else:
        # ログがあるスキルを一覧表示
        if not logs:
            print("実行ログがありません。")
            print("まず skill_observe.py でログを記録してください。")
            return

        print("ログのあるスキル:")
        for skill_name, runs in logs.items():
            analysis = analyze_runs(runs)
            status = "✅" if analysis['avg_score'] >= 0.8 else ("⚠️" if analysis['avg_score'] >= 0.5 else "❌")
            print(f"  {status} {skill_name}: {analysis['count']}件 / 平均スコア {analysis['avg_score']}")

        print("\n特定スキルを分析するには:")
        print("  python .agents/scripts/skill_improve.py --skill <スキル名>")


def main():
    parser = argparse.ArgumentParser(description="スキルの問題点を分析して改善案を生成")
    parser.add_argument("--skill", help="分析するスキル名 (例: line_inbox)")
    parser.add_argument("--all", action="store_true", help="全スキルを分析")
    parser.add_argument("--apply", action="store_true", help="改善案を自動適用（現在は表示のみ）")
    args = parser.parse_args()

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
