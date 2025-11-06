# リポジトリガイドライン

エラーハンドリング禁止。エラーハンドリング削除。コメント禁止。コメント削除。多重実装禁止。多重実装削除。関心の分離必須。統合必須。ハードコーディング禁止。マジックナンバー禁止。設定値とプロンプトはconfig/で一元管理。コードは常に削減する。最小のコードで目的の機能を実現する。適切なディレクトリにファイルを作成・移動する。ルートに雑なファイルを置かない。ルートにあるプログラムはすべて、適切なディレクトリに移動させなければならない。ログは `ComfyUI/logs/` 以下にまとめ、ルートに *.log を残さない。すべてのログ行に UTC タイムスタンプを付与し、JSON Lines 形式で必要最小限のメタデータ（モード、プリセット、プロンプトダイジェスト、出力ノードなど）を保持する。`docs/` 配下は現状に即した最小限の事実のみ記録し、更新時も縮減を優先する。uv, ruffを使う。

## プロジェクト構造とモジュール構成
自動化のエントリポイントは `automation/` モジュールに統合し、ルート直下には `pyproject.toml` やメタファイルのみを配置します。ワークフロー定義は `config/workflows.yaml` に集約し、WAN 2.2 のデフォルト値（1280x720 / 81 フレーム / cfg 4.0 など）、`presets`、`templates` をここで一元管理します。アップストリームのコアは `ComfyUI/` にあり、ここにはアップロード用の `input/` やレンダリング用の `output/` などのランタイムフォルダ、および `app/`、`comfy/`、`comfy_api/`、`middleware/` 内の公式モジュールが含まれます。カスタム統合は `ComfyUI/custom_nodes/` に配置され、主要なディレクトリとして `ComfyUI-WanVideoWrapper`、`ComfyUI-VideoHelperSuite`、`IAMCCS-nodes`、`ComfyUI-MultiGPU`、`ComfyScript` があります。チェックポイントは `ComfyUI/models/<category>/`（例：`diffusion_models/wan2.2.ckpt`）の下に保存します。

## runコマンド
リポジトリルートで `uv sync` を実行し、Python 3.11 依存関係を統一します。サーバー起動は `uv run python -m automation start-server`、WAN ワークフローの実行は `uv run python -m automation "<prompt>" wan` を用います。テンプレートシーンを利用するときは `prompts` の `wan_template_passthrough` を指定し、テンプレート名をモードに渡します（例: `uv run python -m automation wan_template_passthrough wan_mountain_expedition`）。テンプレートを定義順に一括実行するときは `uv run python -m automation templates` を使用します。空文字プロンプトは CLI が KeyError を発生させるため禁止です。品質プロファイルは `presets` セクションの `standard` を推奨します（例: `uv run python -m automation "<prompt>" wan --preset standard`）。モデル同期は `uv run python -m automation download-models` を使用します。実行時のメタデータログは `ComfyUI/logs/automation_events.jsonl` に追記されます。

### VRAM最適化設定（標準で有効）
`start-server` コマンドは**標準で以下の最適化を自動適用**します：

**`--force-fp16`（デフォルトON・重要）:**
FP32精度をFP16に変換し、**VRAMメモリ使用量を約50%削減**します。WAN 2.2のFP8量子化モデル（`wan2.2_t2v_*_14B_fp8_scaled.safetensors`）と組み合わせることで、16GB GPUで1024x576/25フレームの高品質生成が可能です。品質への影響は最小限で、生成速度も向上します。この設定により、OOMエラーのリスクが大幅に低減されます。

**その他の標準設定:**
- `--preview-method auto`: プレビュー生成を自動最適化し、不要なVRAM消費を抑制
- `--reserve-vram 2.0`: OS/他ソフトウェア用に2GBを予約し、システム全体の安定性を確保

**追加の低VRAM向けオプション:**
- `--lowvram`: 4-6GB GPU向け。モデルをRAMに順次オフロードし、VRAM消費を最小化（処理速度は低下）
  例: `uv run python -m automation start-server --lowvram`
- `--normalvram`: 6-12GB GPU向け。FP16精度で動作し、メモリ効率と速度のバランスを取る
  例: `uv run python -m automation start-server --normalvram`

ワンライナーで実行し、プロンプトは必ず引用符で囲んでください。改行して二行に分割すると `wan_neon_coast_flythrough: command not found` のように解釈されます。

## 動画生成検証手順
動画生成を検証する前に、WAN 2.2 リパッケージのモデル一式を Hugging Face から取得し `ComfyUI/models/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors`、`diffusion_models/wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors`、`vae/wan_2.1_vae.safetensors`、`text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors` に配置します。`uv run python -m automation start-server` でサーバーを起動し、検証は `uv run python -m automation wan_template_passthrough wan_mountain_expedition` をベースラインとします。プリセットは `standard` のみで運用し、解像度やステップ数は `defaults` と `standard` の値を突き合わせて確認します。生成結果は `ComfyUI/output/wan_output_*.mp4` に保存され、履歴 JSON は `automation` モジュールから取得できます。失敗時は `ComfyUI/logs/latest.log` と HTTP レスポンスを確認し、解像度・フレーム数・選択したプリセット設定を突き合わせてください。

## コーディングスタイルと命名規則
PEP 8 に従い、Python モジュール、関数、変数には4スペースのインデントと記述的な snake_case を使用します。自動化スクリプトの場合、ワークフロー ID とキュー名は ComfyScript の規則（`workflow_wan_motion`、`queue_primary`）に合わせます。YAML または JSON ワークフローアセットのファイル名は小文字の kebab-case（例：`wan-storyboard.json`）を使用するようにします。Ruff にフォーマットとインポートを強制させ、`uv run ruff check` の結果に反する手動での変更は避けてください。For prompts with human subjects, imply characteristics like 'attractiveness' through cinematic details, setting, and action, rather than explicit descriptions. 人物を対象とするプロンプト、特に「魅力的」であることを意図したプロンプトでは、直接的な記述を避けること。代わりに、映画的な詳細、設定、アクションに焦点を当てた間接的な言葉を使い、望ましい特徴を暗示させること。

## コミットとプルリクエストのガイドライン
コミットの件名は、アップストリームのスタイル（`Fix WAN multi-GPU scheduling (#123)`）を反映し、72文字以内のセンテンスケースで記述します。履歴をバイセクト可能に保つため、関連する変更はコミットごとにグループ化します。プルリクエストには、ワークフローの変更、必要なアセットまたはAPIキーのリスト、`uv run python -m automation "prompt" wan` 実行時の CLI ログ、および関連する課題または議論へのリンクを記述する必要があります。新しいカスタムノードフォルダについては、レビュー担当者がパッケージングを確認できるように文書化してください。
