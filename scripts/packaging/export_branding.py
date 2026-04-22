from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def main() -> int:
    from maintenancetool.branding import CLI_NAME, PRODUCT_EXE_NAME, PRODUCT_ICON_NAME, PRODUCT_NAME

    print(
        json.dumps(
            {
                "product_name": PRODUCT_NAME,
                "product_exe_name": PRODUCT_EXE_NAME,
                "product_icon_name": PRODUCT_ICON_NAME,
                "cli_name": CLI_NAME,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
