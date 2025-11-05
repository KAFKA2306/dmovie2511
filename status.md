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

### ワークフロー最終構成 (automate.py:48-125)
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

## 📂 現在の成果物
- 動画: `ComfyUI/output/wan_output_00001.mp4` (512x320, 16フレーム, 12fps, H.264)
- サムネイル: `ComfyUI/output/wan_output_00001.png`

## 📝 参照
- ワークフロー: automate.py:48-125
- ログ: ComfyUI/logs/start_server.log
