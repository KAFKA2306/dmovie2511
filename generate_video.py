import sys

from automation.script import generate_basic_render


def main() -> None:
    prompt = sys.argv[1] if len(sys.argv) > 1 else "a beautiful landscape"
    output = sys.argv[2] if len(sys.argv) > 2 else "output.mp4"
    generate_basic_render(prompt, output)


if __name__ == "__main__":
    main()
