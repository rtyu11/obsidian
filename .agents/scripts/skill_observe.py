#!/usr/bin/env python3
"""
skill_observe.py
スキル実行後に結果を cognee に記録する。

使い方:
  python .agents/scripts/skill_observe.py \\
    --skill line_inbox \\
    --task "LINEメモを3件処理" \\
    --score 1.0 \\
    --summary "メモ・アイデア・タスクに分類して保存"

スコア基準:
  1.0 = 完全成功
  0.7 = 部分的に成功
  0.3 = ほぼ失敗だが実行できた
  0.0 = 完全失敗

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

# ローカル版 cognee (0.5.4.dev2) のパスを優先追加
LOCAL_COGNEE_LIB = Path(__file__).parent.parent / "cognee" / "lib"
if LOCAL_COGNEE_LIB.exists():
    sys.path.insert(0, str(LOCAL_COGNEE_LIB))

VAULT_PATH = Path(__file__).parent.parent.parent
LOG_FILE = VAULT_PATH / ".agents" / "logs" / "skill_runs.jsonl"


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


def save_to_log(entry: dict):
    """人間が読めるログファイルにも保存"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"  ログ保存: {LOG_FILE.relative_to(VAULT_PATH)}")


async def observe(skill: str, task: str, score: float, summary: str):
    """実行結果を cognee に記録"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "skill": skill,
        "task": task,
        "score": score,
        "summary": summary,
    }

    # ローカルログに保存
    save_to_log(entry)

    # cognee の observe_skill_run API を試みる
    try:
        from cognee.modules.cognify.graph.add_node import observe_skill_run
        result = await observe_skill_run(
            task_text=task,
            selected_skill_id=skill,
            success_score=score,
            result_summary=summary,
        )
        print(f"  cognee 記録完了: {result}")
    except ImportError:
        # フォールバック: cognee の標準 add で記録
        try:
            import cognee
            record = f"""
スキル実行ログ
スキル: {skill}
タスク: {task}
成功スコア: {score}
結果: {summary}
日時: {entry['timestamp']}
"""
            await cognee.add(record, dataset_name=f"skill_runs_{skill}")
            print(f"  cognee フォールバック記録完了")
        except Exception as e:
            print(f"  cognee 記録スキップ（ローカルログのみ）: {e}")

    # スコアに応じたメッセージ
    if score >= 0.8:
        print(f"✅ {skill}: 成功 (score={score})")
    elif score >= 0.4:
        print(f"⚠️  {skill}: 部分成功 (score={score}) - 改善の余地あり")
    else:
        print(f"❌ {skill}: 失敗 (score={score}) - skill_improve.py で分析を推奨")


def main():
    parser = argparse.ArgumentParser(description="スキル実行結果を cognee に記録")
    parser.add_argument("--skill", required=True, help="スキル名 (例: line_inbox)")
    parser.add_argument("--task", required=True, help="実行したタスクの説明")
    parser.add_argument("--score", type=float, required=True, help="成功スコア (0.0〜1.0)")
    parser.add_argument("--summary", required=True, help="結果の要約")
    args = parser.parse_args()

    if not 0.0 <= args.score <= 1.0:
        print("ERROR: --score は 0.0 〜 1.0 の範囲で指定してください。")
        sys.exit(1)

    setup_env()
    asyncio.run(observe(args.skill, args.task, args.score, args.summary))


if __name__ == "__main__":
    main()
