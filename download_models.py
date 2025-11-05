from pathlib import Path
from shutil import copy
from huggingface_hub import hf_hub_download

base_path = Path("ComfyUI/models")

hf_hub_download(
    repo_id="Kijai/WanVideo_comfy",
    filename="umt5-xxl-enc-bf16.safetensors",
    local_dir=base_path / "text_encoders",
    local_dir_use_symlinks=False
)

model_path = hf_hub_download(
    repo_id="Comfy-Org/Wan_2.2_ComfyUI_Repackaged",
    filename="split_files/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
    local_dir_use_symlinks=False
)
dest = base_path / "diffusion_models" / "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"
dest.parent.mkdir(parents=True, exist_ok=True)
copy(model_path, dest)

hf_hub_download(
    repo_id="Kijai/WanVideo_comfy",
    filename="Wan2_1_VAE_bf16.safetensors",
    local_dir=base_path / "vae",
    local_dir_use_symlinks=False
)
