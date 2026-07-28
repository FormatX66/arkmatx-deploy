# Security

## Credential handling

- Never commit host passwords, SSH keys, API keys, tokens, or `.env` files.
- The browser does not place passwords in localStorage, sessionStorage, cookies, URLs, or logs.
- Host login tests are sent only to the same-origin Arkmatx backend over HTTP(S).
- The backend uses the password for one request, returns no secret material, and does not persist the credential.
- Host-test responses use `Cache-Control: no-store` and are rate-limited.
- Persistent credentials require an encrypted vault and a separately supplied `ARKMATX_MASTER_KEY`; that vault is not part of this milestone.

## Network safety

- Network probes and authenticated host tests are disabled by default.
- Enable them only on a controlled backend with `ARKMATX_ALLOW_NETWORK_PROBES=true`.
- Private, loopback, link-local, and reserved targets remain blocked unless an authorized operator explicitly enables private targets.
- TLS certificates are verified by default. Disabling TLS verification is an advanced diagnostic option and must not be used for normal deployment.
- Auto-detection authenticates against only the first supported reachable service, reducing unnecessary login attempts.

## Read-only connection tests

- SSH/SFTP performs a handshake, password authentication, and an SFTP metadata read when available. It runs no shell command.
- FTP/FTPS reads only the current directory.
- cPanel, Plesk, and DirectAdmin use read-only account/API requests.
- No connection test uploads, edits, deletes, renames, or deploys a file.
- The first SSH test reports the host-key fingerprint as unverified. Verify and pin it before allowing deployment.

## Execution safety

Deploy, rollback, restore, and clone actions require explicit confirmation. The current milestone queues and audits commands but intentionally has no silent production executor.

Report security problems privately rather than opening a public issue with sensitive details.
