from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    args = parse_args()
    for raw_path in args.path:
        target = Path(raw_path)
        if not target.exists():
            continue
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        print(f"removed={target}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remove transient CI test artifacts and build directories.")
    parser.add_argument("--path", action="append", default=[], help="File or directory to remove")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
