# Security

## Credential handling

- Never commit host passwords, SSH keys, API keys, tokens, or `.env` files.
- The browser does not place passwords in localStorage, sessionStorage, cookies, URLs, or logs.
- The current host-detection endpoint discards the password after the request and does not persist it.
- Persistent credentials will require an encrypted vault and a separately supplied `ARKMATX_MASTER_KEY`.

## Network safety

Network probes are disabled by default. When enabled, private, loopback, link-local, and reserved targets remain blocked unless an operator explicitly enables private targets in an authorized environment.

## Execution safety

Deploy, rollback, restore, and clone actions require explicit confirmation. The current milestone queues and audits commands but intentionally has no silent production executor.

Report security problems privately rather than opening a public issue with sensitive details.
