# Arkmatx Deploy

Phone-first website deployment control room. This repository is isolated from every existing production website.

## Current milestone

- AI command routing with confirmation gates
- Multi-project and host registry
- BoxBrain status bridge
- Brain Connect connector registry
- Mobile control room
- Safe host detection with network probing disabled by default
- CI, Docker, and GitHub Pages test preview

## Architecture

`Bruce/user -> Arkmatx interface -> BoxBrain controller -> agents/tools -> Brain Connect -> authorized host`

The web UI uses child-simple actions: **Preview**, **Test**, **Ship**, and **Undo**. Advanced details remain available without being required.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Security defaults

- Credentials are never written to Git, browser storage, or logs.
- Host network probing is disabled unless `ARKMATX_ALLOW_NETWORK_PROBES=true`.
- Private/reserved network targets remain blocked unless explicitly allowed.
- Deploy and rollback commands require confirmation.
- This milestone queues and audits actions; it does not silently modify production.

See `SECURITY.md` and `docs/ARCHITECTURE.md`.
