# dmovie2511 — ComfyUI動画生成の自動実行環境

**リポジトリ:** https://github.com/KAFKA2306/dmovie2511

ComfyUIの動画生成ワークフローを、CLIから起動・モデル同期・実行できるようにまとめた自動化プロジェクトです。主にWAN系ワークフローを、`config/workflows.yaml`の設定から再実行できる形で管理します。

同じ設定を保存することで再現性を高めますが、GPU、ドライバー、ComfyUI、カスタムノード、モデル版が異なる場合に、完全に同じ動画や処理時間になることは保証しません。

## できること

- ComfyUIサーバーの起動
- 必要モデルの取得・配置
- 登録済みプロンプトから動画生成
- シーン別テンプレートの実行
- 共通プリセットによるパラメータ上書き
- 複数テンプレートの順次処理
- 実行設定をYAMLで管理

## 必要環境

- Pythonと`uv`
- ComfyUIが動作するGPU環境
- 対応するGPUドライバーとPyTorch
- ワークフローが要求するモデル・カスタムノード
- 動画の後処理に必要な場合はFFmpeg

依存関係の正本は`pyproject.toml`、モデルとワークフローの正本は`config/workflows.yaml`です。

## セットアップ

```bash
uv sync
```

## ComfyUIサーバーを起動

```bash
uv run python -m automation start-server
```

起動後、ComfyUIのURL、待受ポート、GPU認識、カスタムノードの読み込みエラーを確認してください。

## モデルを同期

```bash
uv run python -m automation download-models
```

`config/workflows.yaml`に記録されたモデル情報をもとに取得・配置します。モデルの利用条件、配布元、必要容量を確認してから実行してください。

## 動画を生成

登録済みのプロンプトキーとワークフロー名を指定します。

```bash
uv run python -m automation "wan_default" wan
```

コマンドは1行で実行してください。シェル上で改行すると、後半が別コマンドとして解釈されます。

## テンプレートを使う

```bash
uv run python -m automation "wan_template_passthrough" wan_mountain_expedition
```

`config/workflows.yaml`のテンプレートを定義順に実行する場合:

```bash
uv run python -m automation templates
```

空文字列をプロンプトとして渡す運用は、現在のCLIでは正常に処理できないため使用しません。

## プリセットを使う

```bash
uv run python -m automation "wan_default" wan --preset standard
```

`--preset standard`は、`config/workflows.yaml`の`presets.standard`で既定値を上書きします。

`ti2v_5b_*`系プリセットは、リポジトリに記録された2025年11月6日の検証で24GB GPU上のOOMが発生したため、現在の運用では使用禁止です。別環境で再評価する場合は、GPU、解像度、フレーム数、精度、オフロード設定を記録してください。

## 主な構成

```text
dmovie2511/
├── automation/           # CLIと自動化処理
├── config/               # ワークフロー、モデル、プロンプト、プリセット
├── ComfyUI/              # ComfyUI本体とランタイム
├── docs/                 # 運用・設計資料
└── pyproject.toml        # Python依存関係
```

## 再現性のために保存する情報

- ComfyUIのコミットまたはバージョン
- カスタムノードと各コミット
- モデル名、版、取得元、ファイルハッシュ
- プロンプトとネガティブプロンプト
- seed
- sampler / scheduler
- steps / CFG
- 解像度、フレーム数、FPS
- GPU、VRAM、PyTorch、ドライバー
- 実行日時と生成物

## 注意

- モデルやカスタムノードのライセンスを確認してください
- 自動ダウンロードしたファイルを再配布しないでください
- 高解像度・長時間・大きなバッチはVRAM不足を起こしやすくなります
- 生成動画の内容、人物表現、商用利用可否を公開前に確認してください
- ComfyUIやモデル更新後は、既存ワークフローがそのまま動くとは限りません

**README最終監査:** 2026-08-01
