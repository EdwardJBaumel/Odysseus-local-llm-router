#!/usr/bin/env python3
"""Register host Ollama models in Odysseus ModelEndpoint (integration helper)."""
from __future__ import annotations

import json
import os
import sys
import uuid
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "odysseus")
sys.path.insert(0, APP)
os.chdir(APP)

from core.database import ModelEndpoint, SessionLocal  # noqa: E402

OLLAMA = os.environ.get("OLLAMA_TAGS_URL", "http://127.0.0.1:11434/api/tags")
BASE = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")


def main() -> int:
    tags = json.loads(urllib.request.urlopen(OLLAMA, timeout=10).read())
    models = sorted({m["name"] for m in tags.get("models", [])})
    if len(models) < 2:
        print(f"Need 2+ Ollama models; found {len(models)}", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        ep = (
            db.query(ModelEndpoint)
            .filter(ModelEndpoint.base_url.in_([BASE, BASE.rstrip("/"), "http://127.0.0.1:11434/v1"]))
            .first()
        )
        if ep is None:
            ep = ModelEndpoint(
                id=str(uuid.uuid4()),
                name="Local Ollama",
                base_url=BASE,
                is_enabled=True,
                endpoint_kind="local",
                cached_models=json.dumps(models),
                hidden_models="[]",
            )
            db.add(ep)
            action = "created"
        else:
            ep.cached_models = json.dumps(models)
            ep.is_enabled = True
            ep.endpoint_kind = "local"
            ep.base_url = BASE
            action = "updated"
        db.commit()
        print(f"{action} endpoint {ep.id} with {len(models)} models @ {BASE}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
