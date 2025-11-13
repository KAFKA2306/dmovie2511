from pathlib import Path
from shutil import copy

from huggingface_hub import hf_hub_download

from . import COMFY_ROOT


WAN_TEXT = ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors", "text_encoders")
WAN_VAE = ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/vae/wan_2.1_vae.safetensors", "vae")
WAN_MODEL_Q5 = ("QuantStack/Wan2.2-Animate-14B-GGUF", "Wan2.2-Animate-14B-Q5_K_M.gguf", "diffusion_models")


def model_root() -> Path:
    return COMFY_ROOT / "models"


def download_asset(repo_id: str, filename: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    path = hf_hub_download(repo_id=repo_id, filename=filename, local_dir=str(target.parent), local_dir_use_symlinks=False)
    if Path(path) != target:
        copy(path, target)


def sync_wan_assets() -> None:
    base = model_root()
    text_path = hf_hub_download(repo_id=WAN_TEXT[0], filename=WAN_TEXT[1], local_dir_use_symlinks=False)
    text_dest = base / WAN_TEXT[2] / "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
    text_dest.parent.mkdir(parents=True, exist_ok=True)
    copy(text_path, text_dest)
    model_path = hf_hub_download(repo_id=WAN_MODEL_Q5[0], filename=WAN_MODEL_Q5[1], local_dir_use_symlinks=False)
    dest = base / WAN_MODEL_Q5[2] / WAN_MODEL_Q5[1]
    dest.parent.mkdir(parents=True, exist_ok=True)
    copy(model_path, dest)
    vae_path = hf_hub_download(repo_id=WAN_VAE[0], filename=WAN_VAE[1], local_dir_use_symlinks=False)
    vae_dest = base / WAN_VAE[2] / "wan_2.1_vae.safetensors"
    vae_dest.parent.mkdir(parents=True, exist_ok=True)
    copy(vae_path, vae_dest)
