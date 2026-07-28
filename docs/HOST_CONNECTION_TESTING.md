# Host connection testing

Arkmatx Deploy can perform a single read-only authentication test against common hosting interfaces.

## Supported methods

- SSH with optional SFTP capability check
- FTP
- FTPS, including implicit FTPS on port 990
- cPanel UAPI
- Plesk REST API
- DirectAdmin API
- Generic HTTPS reachability

## Safety rules

- Network testing is disabled by default.
- Enable it only on the trusted Arkmatx backend with `ARKMATX_ALLOW_NETWORK_PROBES=true`.
- Passwords use Pydantic `SecretStr`, are passed only to the selected adapter, are never written to SQLite, Git, browser storage, receipts, or logs, and are omitted from responses.
- Responses use `Cache-Control: no-store`.
- Private, loopback, link-local, and reserved network targets are blocked unless explicitly allowed.
- Tests are rate-limited.
- SSH runs no shell command. The optional SFTP check reads metadata for the current directory only.
- FTP/FTPS reads the current working directory only. It does not upload, rename, or delete files.
- Hosting-panel adapters issue one read-only account or domain-information request.
- A newly observed SSH host key is returned for later pinning; it is not silently trusted for deployment.

## Run the backend

```bash
cp .env.example .env
# Set ARKMATX_ALLOW_NETWORK_PROBES=true in .env
python -m pip install -e ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`, enter a server hostname, username, and password, then choose **Test Connection**.

The static preview is intentionally unable to test credentials by itself. Browsers cannot safely open SSH, SFTP, FTP, or control-panel TCP connections; the FastAPI backend performs those checks.
