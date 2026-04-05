#!/usr/bin/env python3
"""
skill_ingest.py
Vault の .agents/skills/ 配下の全 SKILL.md を cognee のナレッジグラフに取り込む。

使い方:
  python .agents/scripts/skill_ingest.py          # 初回: 全スキルを取り込む
  python .agents/scripts/skill_ingest.py --upsert # 2回目以降: 変更分のみ更新

環境変数:
  GEMINI_API_KEY  Google AI Studio で取得したAPIキー
"""

import os
import sys
import asyncio
from pathlib import Path

# ローカル版 cognee (0.5.4.dev2) のパスを優先追加
LOCAL_COGNEE_LIB = Path(__file__).parent.parent / "cognee" / "lib"
if LOCAL_COGNEE_LIB.exists():
    sys.path.insert(0, str(LOCAL_COGNEE_LIB))

VAULT_PATH = Path(__file__).parent.parent.parent
SKILLS_FOLDER = VAULT_PATH / ".agents" / "skills"
ENV_FILE = VAULT_PATH / ".agents" / "cognee" / ".env"


def setup_env():
    """環境変数と cognee 設定をセット"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: 環境変数 GEMINI_API_KEY が設定されていません。")
        sys.exit(1)

    # cognee の環境変数を設定
    os.environ.setdefault("LLM_PROVIDER", "gemini")
    os.environ.setdefault("LLM_MODEL", "gemini-3-flash-preview")
    os.environ.setdefault("LLM_API_KEY", api_key)
    os.environ.setdefault("EMBEDDING_PROVIDER", "gemini")
    os.environ.setdefault("EMBEDDING_MODEL", "text-embedding-004")
    os.environ.setdefault("EMBEDDING_API_KEY", api_key)

    # 接続テストをバイパス（恒久的なタイムアウト回避設定）
    os.environ["COGNEE_SKIP_CONNECTION_TEST"] = "true"

    # DB 保存先
    db_path = VAULT_PATH / ".agents" / "cognee" / "db"
    db_path.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DB_PATH", str(db_path))


async def ingest(upsert: bool = False):
    """スキルをナレッジグラフに取り込む (0.5.7 標準 API 使用)"""
    try:
        import cognee
    except ImportError as e:
        print(f"ERROR: cognee をインポートできません: {e}")
        sys.exit(1)

    skill_files = list(SKILLS_FOLDER.rglob("SKILL.md"))
    if not skill_files:
        print(f"スキルファイルが見つかりません: {SKILLS_FOLDER}")
        return

    print(f"対象スキル: {len(skill_files)} 件")
    for skill_file in skill_files:
        skill_name = skill_file.parent.name
        print(f"  取り込み中: {skill_name}")
        text = skill_file.read_text(encoding="utf-8")
        # メタデータを付与して add (ベクターストアへの登録)
        await cognee.add(text, dataset_name="vault_skills")

    print("\n✅ スキルの取り込みが完了しました！")
    print("  ※グラフ構築 (cognify) は背景で処理されるか、検索時に自動で行われます。")


async def list_skills_in_graph():
    """グラフに登録されているスキル一覧を表示"""
    try:
        from cognee.modules.cognify.graph.add_node import list_skills
        skills = await list_skills()
        if skills:
            print(f"\n登録スキル一覧 ({len(skills)} 件):")
            for s in skills:
                print(f"  - {s.get('name', s.get('skill_id', '?'))}")
        else:
            print("登録スキルなし")
    except ImportError:
        import cognee
        results = await cognee.search("SKILL.md", query_type="GRAPH_COMPLETION")
        print("グラフ検索結果:", results[:3] if results else "なし")


def main():
    setup_env()

    upsert_mode = "--upsert" in sys.argv
    list_mode = "--list" in sys.argv

    if list_mode:
        asyncio.run(list_skills_in_graph())
    else:
        asyncio.run(ingest(upsert=upsert_mode))


if __name__ == "__main__":
    main()
