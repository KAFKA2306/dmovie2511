# 運用ルール
- 自動化エントリポイントは `automation` モジュールに統合する
- ワークフロー定義は `config/workflows.yaml` で単一管理する
- 依存関係とスタイルは `uv sync` と `uv run ruff check . --fix` で揃える
- ルート直下にスクリプトやログを残さず、生成物は `ComfyUI/` 配下に整理する
