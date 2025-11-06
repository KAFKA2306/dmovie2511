from pathlib import Path
from shutil import copy

from huggingface_hub import hf_hub_download

from . import COMFY_ROOT


WAN_TEXT = ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors", "text_encoders")
WAN_MODEL = ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors", "diffusion_models")
WAN_VAE = ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/vae/wan_2.1_vae.safetensors", "vae")
WAN_MODEL_LOW_NOISE = ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/diffusion_models/wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors", "diffusion_models")
WAN_5B_MODEL = ("Wan-AI/Wan2.2-TI2V-5B", "diffusion_pytorch_model-00001-of-00003.safetensors", "diffusion_models")
WAN_5B_VAE = ("Wan-AI/Wan2.2-TI2V-5B", "Wan2.2_VAE.pth", "vae")
WAN_5B_TEXT = ("Wan-AI/Wan2.2-TI2V-5B", "models_t5_umt5-xxl-enc-bf16.pth", "text_encoders")


def model_root() -> Path:
    return COMFY_ROOT / "models"


def download_asset(repo_id: str, filename: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    path = hf_hub_download(repo_id=repo_id, filename=filename, local_dir=str(target.parent), local_dir_use_symlinks=False)
    if Path(path) != target:
        copy(path, target)


def sync_wan_14b_assets() -> None:
    base = model_root()
    text_path = hf_hub_download(repo_id=WAN_TEXT[0], filename=WAN_TEXT[1], local_dir_use_symlinks=False)
    text_dest = base / WAN_TEXT[2] / "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
    text_dest.parent.mkdir(parents=True, exist_ok=True)
    copy(text_path, text_dest)
    model_path = hf_hub_download(repo_id=WAN_MODEL[0], filename=WAN_MODEL[1], local_dir_use_symlinks=False)
    dest = base / WAN_MODEL[2] / "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"
    dest.parent.mkdir(parents=True, exist_ok=True)
    copy(model_path, dest)
    low_noise_path = hf_hub_download(repo_id=WAN_MODEL_LOW_NOISE[0], filename=WAN_MODEL_LOW_NOISE[1], local_dir_use_symlinks=False)
    low_dest = base / WAN_MODEL_LOW_NOISE[2] / "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors"
    low_dest.parent.mkdir(parents=True, exist_ok=True)
    copy(low_noise_path, low_dest)
    vae_path = hf_hub_download(repo_id=WAN_VAE[0], filename=WAN_VAE[1], local_dir_use_symlinks=False)
    vae_dest = base / WAN_VAE[2] / "wan_2.1_vae.safetensors"
    vae_dest.parent.mkdir(parents=True, exist_ok=True)
    copy(vae_path, vae_dest)


def sync_wan_5b_assets() -> None:
    base = model_root()
    model_path = hf_hub_download(repo_id=WAN_5B_MODEL[0], filename=WAN_5B_MODEL[1], local_dir_use_symlinks=False)
    dest = base / WAN_5B_MODEL[2] / "diffusion_pytorch_model-00001-of-00003.safetensors"
    dest.parent.mkdir(parents=True, exist_ok=True)
    copy(model_path, dest)
    vae_path = hf_hub_download(repo_id=WAN_5B_VAE[0], filename=WAN_5B_VAE[1], local_dir_use_symlinks=False)
    vae_dest = base / WAN_5B_VAE[2] / "Wan2.2_VAE.pth"
    vae_dest.parent.mkdir(parents=True, exist_ok=True)
    copy(vae_path, vae_dest)
    text_path = hf_hub_download(repo_id=WAN_5B_TEXT[0], filename=WAN_5B_TEXT[1], local_dir_use_symlinks=False)
    text_dest = base / WAN_5B_TEXT[2] / "models_t5_umt5-xxl-enc-bf16.pth"
    text_dest.parent.mkdir(parents=True, exist_ok=True)
    copy(text_path, text_dest)


def sync_wan_assets() -> None:
    sync_wan_14b_assets()
    sync_wan_5b_assets()
