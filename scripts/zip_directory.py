"""Create a deterministic ZIP of one directory without bytecode caches.

The Lambda base image used for builds has no ``zip`` or ``find`` binaries, so
the artifacts are assembled with the standard library instead.
"""

import argparse
import zipfile
from pathlib import Path

ALWAYS_EXCLUDED_DIRS = {"__pycache__"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
# ZIP timestamps cannot predate 1980; a fixed value keeps the hash reproducible.
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def zip_directory(
    root: Path, directory: str, archive_path: Path, excluded_dirs: set[str]
) -> int:
    count = 0
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted((root / directory).rglob("*")):
            relative = path.relative_to(root)
            if (
                not path.is_file()
                or excluded_dirs.intersection(relative.parts)
                or path.suffix in EXCLUDED_SUFFIXES
            ):
                continue
            info = zipfile.ZipInfo(relative.as_posix(), date_time=FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (path.stat().st_mode & 0o777 | 0o444) << 16
            archive.writestr(info, path.read_bytes())
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="directory the archive is relative to")
    parser.add_argument("directory", help="directory below root to archive")
    parser.add_argument("archive", type=Path, help="ZIP file to create")
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="directory name to skip at any depth (repeatable)",
    )
    args = parser.parse_args()

    count = zip_directory(
        args.root,
        args.directory,
        args.archive,
        ALWAYS_EXCLUDED_DIRS | set(args.exclude_dir),
    )
    if count == 0:
        raise SystemExit(f"No files found below {args.root / args.directory}")
    print(f"Wrote {count} files to {args.archive}")


if __name__ == "__main__":
    main()
