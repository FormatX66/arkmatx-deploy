# Architecture

## Canonical flow

`User -> Arkmatx interface -> BoxBrain controller -> specialized agents/tools -> Brain Connect -> authorized target`

## Components

- **Arkmatx interface:** phone-first control room and simple workflow.
- **Command router:** converts plain language into typed, auditable tasks.
- **Safety gate:** requires confirmation for production-changing actions.
- **Project registry:** websites, repositories, environments, and status.
- **Host adapters:** SSH/SFTP, FTP/FTPS, cPanel, Plesk, DirectAdmin, and HTTPS APIs.
- **BoxBrain bridge:** optional authenticated health/status integration.
- **Brain Connect:** future execution boundary for hosts, machines, APIs, and files.

## Deployment lifecycle

`Validate -> Build -> Preview -> Backup -> Deploy -> Verify -> Receipt`

A verification failure must produce an automatic rollback recommendation and, once an executor is enabled, an automatic restore from the pre-deploy backup.

## Current boundary

This repository is a safe control-plane alpha. It demonstrates the user flow, registry, command parser, connector model, and confirmation gates. Real production execution remains disabled until the credential vault, adapter tests, and rollback verification pass.
