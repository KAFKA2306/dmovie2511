# ComfyUI 自動動画生成


このプロジェクトは、[ComfyUI](https://github.com/comfyanonymous/ComfyUI) を使用して、WAN ビデオモデルを活用した動画生成を自動化するためのツールです。


## 主な機能


- ComfyUI を使用したテキストからの動画生成
- WAN  ビデオモデルのサポート
- 単一プロンプトおよびバッチ処理による動画生成
- Python スクリプトによる簡単な操作


## 必須コンポーネント


本プロジェクトを実行するには、以下のコンポーネントが必要です。


### モデル


**WAN モデル:**


- **ダウンロード元:** [Hugging Face - Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/tree/main)
- **配置場所:**
  - `ComfyUI/models/diffusion_models`
  - `ComfyUI/models/text_encoders`
  - `ComfyUI/models/vae`


### カスタムノード


以下のカスタムノードが `ComfyUI/custom_nodes/` ディレクトリにインストールされている必要があります。


- [ComfyUI-WanVideoWrapper](https://github.com/kijai/ComfyUI-WanVideoWrapper)
- [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite)
- [IAMCCS-nodes](https://comfy.icu/extension/IAMCCS__IAMCCS-nodes)
- [ComfyScript](https://github.com/Chaoses-Ib/ComfyScript)
- (オプション) [ComfyUI-MultiGPU](https://github.com/pollockjj/ComfyUI-MultiGPU)


## セットアップ


1. **依存関係のインストール:**


   ```bash
   uv sync
   ```


2. **カスタムノードの要求事項をインストール:**


   ```bash
   uv pip install -r ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper/requirements.txt
   uv pip install -r ComfyUI/custom_nodes/ComfyUI-VideoHelperSuite/requirements.txt
   uv pip install -e ComfyUI/custom_nodes/ComfyScript[default]
   ```


## 使用方法


1. **ComfyUI サーバーの起動:**


   ```bash
   uv run python start_server.py
   ```


2. **動画の生成:**


   **単一プロンプト (WAN):**


   ```bash
   uv run python automate.py "cinematic sunset over mountains" wan
   ```


   **バッチ生成:**


   `automation.core` の `batch_generate` 関数を使用して、複数のプロンプトから動画を生成できます。


   ```python
   import asyncio
   from automation.core import batch_generate


   prompts = [
       "scene 1",
       "scene 2",
       "scene 3"
   ]


   asyncio.run(batch_generate(prompts, mode="wan"))
   ```


## プロジェクト構成


- **`automate.py`**: 動画生成を自動化するメインスクリプトです。
- **`automation/`**: クライアント、ワークフロー生成、モデル同期などの自動化ロジックを保持します。
- **`start_server.py`**: ComfyUI サーバーを起動します。
- **`ComfyUI/`**: ComfyUI の本体と関連ファイルが含まれます。
- **`ComfyUI/custom_nodes/`**: カスタムノードが配置されます。
- **`ComfyUI/output/`**: 生成された動画が保存されます。
