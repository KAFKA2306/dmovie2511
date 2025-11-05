# ComfyUI 自動動画生成

WAN モデル向けの ComfyUI ワークフローを一貫した品質で実行するための極小オーケストレーションレイヤーです。単一のエントリポイントに統合された CLI が、サーバー起動からモデル同期、バッチ生成までをカバーし、環境の差異を吸収します。

## 価値
- 1 つの `automation` モジュールからすべての自動化を呼び出せるため運用手順が単純化される
- declared ワークフロー定義 (`config/workflows.yaml`) により再現性の高い動画生成が行える
- `uv` + `ruff` パイプラインで依存関係とスタイルを機械的に保証できる

## 必須アセット
- WAN ファミリーのモデルを Hugging Face から取得し、`ComfyUI/models/diffusion_models`・`text_encoders`・`vae` に配置する
- カスタムノード (`ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper` など) を upstream 手順どおりに設置する

## セットアップ
```bash
uv sync
```

## 使い方
- サーバー起動: `uv run python -m automation start-server`
- モデル同期: `uv run python -m automation download-models`
- 単一生成 (WAN 既定値): `uv run python -m automation "cinematic shot of a sunset over mountains" wan`
- バッチ生成: プロンプトを `||` 区切りで渡す (例: `"scene1||scene2||scene3" wan`)
- ワークフロープリセット: `config/workflows.yaml` のモード名を第 2 引数に指定

## ディレクトリ構成
- `automation/` 自動化エントリポイントとワークフロー/モデル同期ロジック
- `config/` ワークフロー定義などの実行時設定
- `ComfyUI/` コア実装とランタイムフォルダ
- `docs/` ドキュメント、`AGENTS.md` は運用ガイドライン
- `pyproject.toml`・`uv.lock` 依存関係管理
