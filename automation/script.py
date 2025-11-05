from pathlib import Path

from . import ensure_comfy_path


def generate_basic_render(prompt: str, output_path: str = "output.mp4") -> str:
    ensure_comfy_path()
    from comfy_script.runtime import load
    from comfy_script.runtime.nodes import (
        Workflow,
        CheckpointLoaderSimple,
        CLIPTextEncode,
        EmptyLatentImage,
        KSampler,
        VAEDecode,
        SaveImage,
    )

    load()
    prefix = Path(output_path).stem
    with Workflow():
        model, clip, vae = CheckpointLoaderSimple("v1-5-pruned-emaonly.safetensors")
        conditioning = CLIPTextEncode(prompt, clip)
        conditioning_negative = CLIPTextEncode("", clip)
        latent = EmptyLatentImage(512, 512, 1)
        latent = KSampler(
            model,
            positive=conditioning,
            negative=conditioning_negative,
            latent_image=latent,
            seed=42,
            steps=20,
            cfg=7.0,
            sampler_name="euler",
            scheduler="normal",
            denoise=1.0,
        )
        image = VAEDecode(latent, vae)
        SaveImage(image, filename_prefix=prefix)
    return output_path
