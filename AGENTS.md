# リポジトリガイドライン

エラーハンドリング禁止。エラーハンドリング削除。コメント禁止。コメント削除。多重実装禁止。多重実装削除。関心の分離必須。統合必須。ハードコーディング禁止。コードは常に削減する。最小のコードで目的の機能を実現する。適切なディレクトリにファイルを作成・移動する。ルートに雑なファイルを置かない。ルートにあるプログラムはすべて、適切なディレクトリに移動させなければならない。ログは `ComfyUI/logs/` 以下にまとめ、ルートに *.log を残さない。`docs/` 配下は現状に即した最小限の事実のみ記録し、更新時も縮減を優先する。uv, ruffを使う。

## プロジェクト構造とモジュール構成
自動化のエントリポイントは `automation/` モジュールに統合し、ルート直下には `pyproject.toml` やメタファイルのみを配置します。ワークフロー定義は `config/workflows.yaml` に集約します。アップストリームのコアは `ComfyUI/` にあり、ここにはアップロード用の `input/` やレンダリング用の `output/` などのランタイムフォルダ、および `app/`、`comfy/`、`comfy_api/`、`middleware/` 内の公式モジュールが含まれます。カスタム統合は `ComfyUI/custom_nodes/` に配置され、主要なディレクトリとして `ComfyUI-WanVideoWrapper`、`ComfyUI-VideoHelperSuite`、`IAMCCS-nodes`、`ComfyUI-MultiGPU`、`ComfyScript` があります。チェックポイントは `ComfyUI/models/<category>/`（例：`diffusion_models/wan2.2.ckpt`）の下に保存します。

## runコマンド
リポジトリルートから `uv sync` を使用して、ComfyUI と自動化スクリプトの両方の Python 3.11 依存関係を解決します。`uv run python -m automation start-server` をバックグラウンド起動したまま維持し、`uv run python -m automation "prompt" wan` でスクリプト化されたジョブを送信します。モデル同期は `uv run python -m automation download-models` を使用します。

## 動画生成検証手順
動画生成を検証する前に、WAN モデルを Hugging Face から取得し `ComfyUI/models/diffusion_models/` および関連する `vae/`、`text_encoders/` に配置します。`uv run python -m automation start-server` でサーバーを起動後、WAN 検証は `uv run python -m automation "シネマティックな朝焼けのタイムラプスショット" wan` を実行します。成功時は `ComfyUI/output/` に `wan_output_*.mp4` が保存され、`automation` モジュールから履歴 JSON が得られます。失敗時は `ComfyUI/logs/latest.log` のサーバーログと HTTP 応答内容を確認し、解像度・フレーム数・コーデック情報を検証してください。

## コーディングスタイルと命名規則
PEP 8 に従い、Python モジュール、関数、変数には4スペースのインデントと記述的な snake_case を使用します。自動化スクリプトの場合、ワークフロー ID とキュー名は ComfyScript の規則（`workflow_wan_motion`、`queue_primary`）に合わせます。YAML または JSON ワークフローアセットのファイル名は小文字の kebab-case（例：`wan-storyboard.json`）を使用するようにします。Ruff にフォーマットとインポートを強制させ、`uv run ruff check` の結果に反する手動での変更は避けてください。

## コミットとプルリクエストのガイドライン
コミットの件名は、アップストリームのスタイル（`Fix WAN multi-GPU scheduling (#123)`）を反映し、72文字以内のセンテンスケースで記述します。履歴をバイセクト可能に保つため、関連する変更はコミットごとにグループ化します。プルリクエストには、ワークフローの変更、必要なアセットまたはAPIキーのリスト、`uv run python -m automation "prompt" wan` 実行時の CLI ログ、および関連する課題または議論へのリンクを記述する必要があります。新しいカスタムノードフォルダについては、レビュー担当者がパッケージングを確認できるように文書化してください。
