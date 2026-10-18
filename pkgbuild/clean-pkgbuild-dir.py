#! /usr/bin/python3

import pathlib
import shutil

KEEP_NAMES = {"README.md", "PKGBUILD"}


def main():
    pkgbuild_dir = pathlib.Path(__file__).resolve().parent
    if not (pkgbuild_dir / "PKGBUILD").is_file():
        raise SystemExit(f"Refusing to clean {pkgbuild_dir}: PKGBUILD is missing")

    keep = set(KEEP_NAMES)
    keep.add(pathlib.Path(__file__).name)

    for entry in pkgbuild_dir.iterdir():
        if entry.name in keep:
            continue
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()
        print(f"removed {entry.name}")


if __name__ == "__main__":
    main()
