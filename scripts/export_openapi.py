"""Write the API's OpenAPI schema to web/openapi.json.

Usage:
    python scripts/export_openapi.py          # write the file
    python scripts/export_openapi.py --check  # fail if the file is out of date (CI)

The web interface generates its TypeScript types from this file
(`npm run gen:api` in web/), so the frontend follows the API contract. Building
the schema does not load or download the model.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Final

from ncm_classifier.api.config import Settings
from ncm_classifier.api.main import create_app

OUTPUT: Final = Path("web/openapi.json")


def render() -> str:
    schema = create_app(Settings(_env_file=None)).openapi()
    return json.dumps(schema, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = render()
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != content:
            raise SystemExit(f"{OUTPUT} is out of date: run python scripts/export_openapi.py")
        return
    OUTPUT.write_text(content, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
