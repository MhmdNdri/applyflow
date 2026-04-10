from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    if not os.getenv("CLERK_ISSUER") or not os.getenv("CLERK_JWKS_URL"):
        os.environ["AUTH_ENABLED"] = "false"

    from jobfit_api.main import create_app
    from jobfit_api.settings import ApiSettings

    output_path = root / "frontend" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    settings = ApiSettings.from_env(root)
    app = create_app(settings)
    schema = app.openapi()
    output_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
