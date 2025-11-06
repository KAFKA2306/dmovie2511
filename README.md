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
    - `config/workflows.yaml` の `prompts` セクションに登録したプロンプトキーと、ワークフロー名を指定して実行します。
    - `wan` ワークフローのデフォルト設定で動画を生成する場合は、一行でプロンプトを引用符に包んで実行します（改行すると `wan_neon_coast_flythrough: command not found` になるため注意してください）。

    ```bash
    uv run python -m automation "wan_default" wan
    ```

- **テンプレートの利用**:
    - `config/workflows.yaml` の `templates` に、WAN ワークフロー向けのシーン別設定がまとまっています。
    - テンプレート固有のプロンプトを使う場合は、`prompts` の `wan_template_passthrough` を指定し、テンプレート名（例: `wan_mountain_expedition`）をモードとして指定します。

    ```bash
    uv run python -m automation "wan_template_passthrough" wan_mountain_expedition
    ```

    - テンプレートを `config/workflows.yaml` の定義順にまとめて実行する場合は `uv run python -m automation templates` を使用します。
    - 空文字プロンプトを渡す運用は CLI が KeyError を発生させるため禁止です。

- **プリセットの利用**:
    - 共通パラメータの切り替えは `config/workflows.yaml` の `presets` セクションにある `standard` プリセットで統一しています。
    - `ti2v_5b_*` 系プリセットは 2025-11-06T06:00:00Z 時点で 24GB GPU でも OOM が再現されたため使用禁止です。
    - 実行時に `--preset standard` を付与すると、`standard` の設定で `defaults` が上書きされます。

    ```bash
    uv run python -m automation "wan_default" wan --preset standard
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
