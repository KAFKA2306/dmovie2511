import asyncio
import sys

from automation.core import batch_generate, generate_video


async def main() -> None:
    if len(sys.argv) > 2:
        prompts = sys.argv[1].split("||")
        mode = sys.argv[2]
        await batch_generate(prompts, mode)
    else:
        prompt = sys.argv[1] if len(sys.argv) > 1 else "cinematic shot of a sunset over mountains"
        mode = sys.argv[2] if len(sys.argv) > 2 else "wan"
        await generate_video(prompt, mode)


if __name__ == "__main__":
    asyncio.run(main())
