from __future__ import annotations

import json
from pathlib import Path

from app.main import create_app

app = create_app()
Path('/workspace/openapi.json').write_text(json.dumps(app.openapi(), indent=2))
print('Wrote /workspace/openapi.json')
