# ComfyUI 自動動画生成

WANおよびKlingビデオモデルを使用したComfyUIによる映画作成の完全自動化。

## セットアップ

```bash
uv sync
```

## モデル

モデルをダウンロード:

**WANモデル:**
- https://huggingface.co/Kijai/WanVideo_comfy/tree/main
- 配置場所: `ComfyUI/models/diffusion_models`, `ComfyUI/models/text_encoders`, `ComfyUI/models/vae`


## 使用方法

サーバーを起動:
```bash
uv run python start_server.py
```

動画を生成 (WAN):
```bash
uv run python automate.py "cinematic sunset over mountains" wan
```

バッチ生成:
```python
from automate import batch_generate

prompts = [
    "scene 1",
    "scene 2",
    "scene 3"
]

asyncio.run(batch_generate(prompts, mode="wan"))
```

## リポジトリ

- comfyanonymous/ComfyUI
- kijai/ComfyUI-WanVideoWrapper
- KwaiVGI/ComfyUI-KLingAI-API
- Kosinkadink/ComfyUI-VideoHelperSuite
- Lightricks/ComfyUI-LTXVideo


 必須リポジトリ

  - comfyanonymous/ComfyUI プロジェクトルートにあり、グラフUIバックエンド、HTTP/WebSocket API、およびプログラムで駆動するスケジューラを提供します。(github.com (https://github.com/comfyanonymous/ComfyUI?
    utm_source=openai))
  - custom_nodes/ComfyUI-WanVideoWrapper; Wan 2.xのテキスト-ビデオ、画像-ビデオ、ビデオ-ビデオサンプラー、およびエンドツーエンド生成に必要なエンコーダ/デコーダノードをラップします。(comfyui.org (https://comfyui.org/
    en/ai-generated-video-workflow-guide?utm_source=openai))
  - custom_nodes/ComfyUI-KLingAI-API; オプションのKling APIブリッジで、同じComfyUIワークフローでWANローカル推論とクラウドレンダリングを切り替えることができます。(github.com (https://github.com/KwaiVGI/ComfyUI-
    KLingAI-API?utm_source=openai))
  - custom_nodes/ComfyUI-VideoHelperSuite; VHSのロード/結合/エクスポート、オーディオ多重化、およびフォーマットプリセットを追加します。自動化中にフレームをMP4/WEBMに結合するために必要です。(github.com (https://github.com/Kosinkadink/
    ComfyUI-VideoHelperSuite?utm_source=openai))
  - custom_nodes/IAMCCS-nodes; ネイティブWANAnimate LoRAインジェクションを修正し、デュアルマスキングとループ拡張ユーティリティを追加するため、必要に応じてラッパーなしで作業できます。(comfy.icu (https://comfy.icu/extension/
    IAMCCS__IAMCCS-nodes?utm_source=openai))
  - custom_nodes/ComfyScript; 編集可能なモードでインストールし、Pythonとしてワークフローを作成し、プロンプトをテンプレート化し、自動化スクリプトからジョブキューをオーケストレーションします。(github.com (https://github.com/Chaoses-Ib/ComfyScript?
    utm_source=openai))
  - オプション: custom_nodes/ComfyUI-MultiGPU 長いクリップやマルチGPU WAN実行のためにVRAMオフロード/ブロックスワップが必要な場合; WanVideoWrapperスケジュールと統合されます。(github.com (https://github.com/pollockjj/
    ComfyUI-MultiGPU?utm_source=openai))

  自動化スタック

  - ComfyScriptを軽量APIクライアント (comfyui-api-clientまたはcomfyui-workflow-client) と組み合わせて、UV管理スクリプトまたはサービスからの非同期ジョブ送信、進捗ポーリング、結果取得を行います。
    (pypi.org (https://pypi.org/project/comfyui-api-client?utm_source=openai))
  - WANワークフローがローカルGPUの利用可能性を待っている間、Klingノードをフォールバック/クラウドレンダリングに使用します。このノードはconfig.iniを介してAPIキー設定を公開するため、ワークフローグラフの外にシークレットを保持できます。
    (github.com (https://github.com/KwaiVGI/ComfyUI-KLingAI-API?utm_source=openai))
  - IAMCCSネイティブノードをWanVideoWrapperと並行して保持します。現在の多くのWAN Animate V2ワークフローは、ネイティブLoRAサポートとパスアニメーションのようなラッパー専用ユーティリティを組み合わせるために両方を混在させています。(comfy.icu (https://comfy.icu/
    extension/IAMCCS__IAMCCS-nodes?utm_source=openai))

  uv セットアップ (コメントなし)

  cd /path/to/projects
  git clone https://github.com/comfyanonymous/ComfyUI.git
  cd ..
  uv pip install -r custom_nodes/ComfyUI-WanVideoWrapper/requirements.txt
  uv pip install -r custom_nodes/ComfyUI-KLingAI-API/requirements.txt
  uv pip install -r custom_nodes/ComfyUI-VideoHelperSuite/requirements.txt
  uv pip install -e custom_nodes/ComfyScript[default]

  - KijaiのHugging FaceミラーからWAN 2.xチェックポイント、VAE、UMT5テキストエンコーダをダウンロードし、自動ジョブを実行する前にそれぞれComfyUI/models/diffusion_models、ComfyUI/models/vae、ComfyUI/models/text_encodersの下に配置します。
    (reddit.com (https://www.reddit.com/r/comfyui/comments/1j2v3lc?utm_source=openai))
  - KlingまたはIAMCCSネイティブノードに依存している場合、対応するLoRAとプリプロセッサを専用のサブフォルダ (loras/, controlnet/) に保持し、スクリプト化されたワークフローが手動UI編集なしでモデルセットをホットスワップできるようにします。
    (comfy.icu (https://comfy.icu/extension/IAMCCS__IAMCCS-nodes?utm_source=openai))

  次のステップ

  - 各カスタムノードがクリーンにロードされることを検証し (uv run python main.py --listen 127.0.0.1 --port 8188)、スクリプトを接続する前に依存関係のギャップについてコンソールログをキャプチャします。
  - WANワークフローをロードし、プロンプト/期間をオーバーライドし、VHS結合をトリガーし、最終レンダリングをアップロードするComfyScriptテンプレートをスクリプト化します。まず短い16〜32フレームのクリップでテストします。

■ '/init' is disabled while a task is in progress.
  - ステージングブランチで定期的なgit pull + uv pip install -r ...の実行をスケジュールします。WANノードは急速に進化するため、本番自動化のために既知の良好なコミットをフリーズします。# dmovie2511
