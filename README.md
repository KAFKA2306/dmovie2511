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

- **テンプレートの利用**:
    - `config/workflows.yaml` の `templates` に、WAN ワークフロー向けのシーン別設定がまとまっています。
    - テンプレート固有のプロンプトを使う場合は、プロンプトを空文字にしてテンプレート名（例: `wan_mountain_expedition`）をモードとして指定します。

    ```bash
    uv run python -m automation "" wan_mountain_expedition
    ```

- **プリセットの切り替え**:
    - 品質や解像度などの共通パラメータは、`config/workflows.yaml` の `presets` セクションに集約します。
    - 実行時に `--preset` オプションを付けると、定義済みのプリセット（例: `standard`, `high_quality`, `dual_pass`）で `defaults` を上書きできます。
    - 利用可能なプリセット名は `config/workflows.yaml` を確認してください。

    ```bash
    uv run python -m automation "aerial establishing shot of a valley" wan --preset high_quality
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
