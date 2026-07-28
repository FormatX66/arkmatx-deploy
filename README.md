# Arkmatx Deploy

Phone-first website deployment control room. This repository is isolated from every existing production website.

## Current milestone

- AI command routing with confirmation gates
- Multi-project and host registry
- BoxBrain status bridge
- Brain Connect connector registry
- Mobile control room
- Read-only host authentication tests for SSH/SFTP, FTP/FTPS, cPanel, Plesk, DirectAdmin, and HTTPS
- CI, Docker, and static mobile preview

## Architecture

`Bruce/user -> Arkmatx interface -> BoxBrain controller -> agents/tools -> Brain Connect -> authorized host`

The web UI uses child-simple actions: **Preview**, **Test**, **Ship**, and **Undo**. Advanced details remain available without being required.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
cp .env.example .env        # Windows: copy .env.example .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Enable a real host login test

Host authentication is opt-in. In `.env`, set:

```env
ARKMATX_ALLOW_NETWORK_PROBES=true
```

Restart the backend, open the same Arkmatx URL, and use **Connect a Host**. The tester performs one read-only authentication attempt, reports the detected protocol/capabilities, then discards the password. It does not run a shell command, upload a file, or save credentials.

For SSH/SFTP, the first test reports the server host-key fingerprint. Pin and verify that fingerprint before any future deployment action.

## Security defaults

- Credentials are never written to Git, browser storage, URLs, receipts, or application logs.
- The connection-test endpoint is same-origin only, rate-limited, and returns `Cache-Control: no-store`.
- Host network probing is disabled unless `ARKMATX_ALLOW_NETWORK_PROBES=true`.
- Private/reserved network targets remain blocked unless explicitly allowed in an authorized environment.
- TLS certificates are verified by default.
- Deploy and rollback commands require confirmation.
- This milestone tests access only; it does not silently modify production.

See `SECURITY.md` and `docs/ARCHITECTURE.md`.
