import subprocess

from automation import COMFY_ROOT


def main() -> None:
    subprocess.run([
        "uv",
        "run",
        "python",
        str(COMFY_ROOT / "main.py"),
        "--listen",
        "127.0.0.1",
        "--port",
        "8188",
    ])


if __name__ == "__main__":
    main()
