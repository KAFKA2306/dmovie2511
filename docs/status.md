# 現状共有（2025-11-06）
- `config/workflows.yaml` で WAN 2.2 の defaults を `width:512`、`height:512`、`frames:81`、`cfg:4.0`、`steps:30` に統一済み。
- `scheduling.timezone` は `Asia/Tokyo`、ウィンドウは 03:00–05:00 JST に固定。
- 2025-11-06T03:00:00+09:00 実行予定のジョブ: `wan_modern_lab`（preset `standard`）。`uv run python -m automation scheduled` で確認可能。
- 予約ジョブを即時に流す場合は `uv run python -m automation scheduled --run-now --preset standard` を使用。
