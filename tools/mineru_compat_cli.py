"""Run the installed MinerU CLI with the version-scoped batch OCR guard."""

from _mineru_ocr_compat import install


def main() -> None:
    install()
    # Import after installation: the backend imports the guarded function by name.
    from mineru.kit.main import main as mineru_main

    mineru_main()


if __name__ == "__main__":
    main()
