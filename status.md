# WAN T2V検証 - 最終ステータス (2025-11-05)

## ✅ 最新状況

### モデル配置
```
✓ umt5-xxl-enc-bf16.safetensors                     11GB  (text_encoders/)
✓ wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors 14GB  (diffusion_models/)
✓ Wan2_1_VAE_bf16.safetensors                       243MB (vae/)
```

### 最新実行結果
- `uv run python start_server.py` → 正常起動 (ComfyUI 0.3.67)。
- `uv run python automate.py "シネマティックな朝焼けのタイムラプスショット" wan` → 成功。`prompt_id=6e4ec9ea-1a71-4216-a3fe-8e1e8711b81d`。
- 出力生成: `ComfyUI/output/wan_output_00001.mp4` (118,787 bytes) とサムネイル `wan_output_00001.png`。

### ワークフロー最終構成 (automation/core.py:52-127)
```
[1] WanVideoTextEncodeCached → text_embeds
[2] WanVideoModelLoader (load_device=offload_device) → model
[3] WanVideoVAELoader → vae
[4] WanVideoEmptyEmbeds → image_embeds
[5] WanVideoSampler → samples
[6] WanVideoDecode (tile_x=272, tile_y=272) → images
[7] VHS_VideoCombine → wan_output_*.mp4
```

## 🚀 再実行手順

```bash
uv run python start_server.py
```

別ターミナル:
```bash
uv run python automate.py "シネマティックな朝焼けのタイムラプスショット" wan
```

## 📂 生成結果
- **動画**: `ComfyUI/output/wan_output_00001.mp4`
  - 解像度: 512x320
  - フレーム数: 13フレーム
  - フレームレート: 12fps
  - 時間: 1.08秒
  - コーデック: H.264
  - サイズ: 116KB
- **サムネイル**: `ComfyUI/output/wan_output_00001.png`

## ⏱️ パフォーマンス
- テキストエンコード: <1秒 (キャッシュ利用)
- モデルロード: 13秒 (14B T2V, 1095パラメータ)
- サンプリング: 71秒 (24ステップ, 約3秒/ステップ)
- VAEデコード+動画保存: 17秒
- **総実行時間**: 101.66秒
- **最大VRAM使用量**: 13.8GB / 16GB

## 📝 参照
- ワークフロー: automation/core.py:52-127
- ログ: ComfyUI/logs/start_server.log
