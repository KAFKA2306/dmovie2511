import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "ComfyUI"))

from comfy_script.runtime import load
from comfy_script.runtime.nodes import *


async def generate_video(prompt: str, output_path: str = "output.mp4"):
    load()

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
        SaveImage(image, filename_prefix="output")

    return output_path


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "a beautiful landscape"
    output = sys.argv[2] if len(sys.argv) > 2 else "output.mp4"
    asyncio.run(generate_video(prompt, output))
