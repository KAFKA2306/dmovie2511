# Automation Module

This module contains the automation entry points for the ComfyUI project.

## Usage

- To start the local node server: `uv run python -m automation start-server`
- To submit a scripted job: `uv run python -m automation "wan_default" wan --preset standard` (keep the command on one line; multi-line input is rejected)
- To synchronize models: `uv run python -m automation download-models`
- Do not use `ti2v_5b_*` presets; 24GB GPUs OOM-ed on 2025-11-06T06:00:00Z.
