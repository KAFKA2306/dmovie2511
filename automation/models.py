from pathlib import Path
from shutil import copy

from huggingface_hub import hf_hub_download

from . import COMFY_ROOT


WAN_TEXT = ("Kijai/WanVideo_comfy", "umt5-xxl-enc-bf16.safetensors", "text_encoders")
WAN_MODEL = ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors", "diffusion_models")
WAN_VAE = ("Kijai/WanVideo_comfy", "Wan2_1_VAE_bf16.safetensors", "vae")


def model_root() -> Path:
    return COMFY_ROOT / "models"


def download_asset(repo_id: str, filename: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    path = hf_hub_download(repo_id=repo_id, filename=filename, local_dir=str(target.parent), local_dir_use_symlinks=False)
    if Path(path) != target:
        copy(path, target)


def sync_wan_assets() -> None:
    base = model_root()
    download_asset(WAN_TEXT[0], WAN_TEXT[1], base / WAN_TEXT[2] / WAN_TEXT[1])
    model_path = hf_hub_download(repo_id=WAN_MODEL[0], filename=WAN_MODEL[1], local_dir_use_symlinks=False)
    dest = base / WAN_MODEL[2] / "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"
    dest.parent.mkdir(parents=True, exist_ok=True)
    copy(model_path, dest)
    download_asset(WAN_VAE[0], WAN_VAE[1], base / WAN_VAE[2] / WAN_VAE[1])
