# ComfyUI 自動動画生成プロジェクト

このプロジェクトは、[ComfyUI](https://github.com/comfyanonymous/ComfyUI) を使用して、高品質な動画を安定して自動生成するための環境を提供します。特に、WAN モデルのような複雑なワークフローを、誰でも簡単に実行できるように設計されています。

CLI ツールを通じて、サーバーの起動、モデルの同期、動画の生成まで、一貫した操作で実行できます。

## ✨ 主な特徴

- **シンプルな操作**: `automation` モジュールに統一されたコマンドを通じて、すべての操作を簡単に行えます。
- **再現性の高い動画生成**: `config/workflows.yaml` に定義されたワークフロー設定により、誰が実行しても同じ品質の動画を生成できます。
- **クリーンな環境**: `uv` と `ruff` を利用した開発パイプラインにより、依存関係の解決やコーディングスタイルを自動で統一します。

## 使い方

### サーバーの起動

動画生成の前に、まず ComfyUI サーバーを起動する必要があります。

```bash
uv run python -m automation start-server
```

### モデルの同期

`download-models` コマンドを使用すると、`config/workflows.yaml` に定義されたモデルを自動でダウンロード・配置できます。

```bash
uv run python -m automation download-models
```

### 動画の生成

- **基本的な使い方**:
    - プロンプト (動画の説明) と、ワークフロー名を指定して実行します。
    - `wan` ワークフローのデフォルト設定で動画を生成する場合:

    ```bash
    uv run python -m automation "a cinematic shot of a sunset over mountains" wan
    ```

- **バッチ処理**:
    - 複数のプロンプトを `||` で区切ることで、一度に複数の動画を生成できます。

    ```bash
    uv run python -m automation "scene1||scene2||scene3" wan
    ```

- **プリセットの利用**:
    - `config/workflows.yaml` には、あらかじめいくつかのプリセットが定義されています。
    - プリセット名を指定するだけで、特定のパラメータ設定で動画を生成できます。

    ```bash
    uv run python -m automation "a beautiful cinematic shot" wan_cinematic_evening
    ```

## プロジェクトの構造

```
.
├── automation/      # 自動化スクリプトのすべて
├── config/          # ワークフローの定義ファイル
├── ComfyUI/         # ComfyUI のコアとランタイム
├── docs/            # プロジェクトのドキュメント
├── pyproject.toml   # プロジェクトの依存関係
```