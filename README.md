# Plant Tracker

A self-hosted plant collection manager: photograph a plant, get it identified,
get care instructions generated for it, and keep a rendered note per plant in an
Obsidian vault.

FastAPI backend plus a Flutter Android client (`app_flutter/`).

## Features

- **Species identification** from a photo via the [Pl@ntNet](https://my-api.plantnet.org/) API,
  returning ranked candidates with confidence scores
- **Disease and variety identification** on the same pipeline
- **AI-generated care instructions** per species (watering, light, soil, temperature)
- **Species enrichment** from GBIF and Wikipedia — taxonomy, native range, summary text
- **Photo history** per plant, stored on disk with the DB holding metadata only
- **Obsidian vault sync** — renders a markdown note per plant, either to a local
  path or to a remote host over rsync/ssh

## Stack

- FastAPI + SQLModel + SQLite
- Flutter (Android client)
- External APIs: Pl@ntNet, Anthropic, GBIF, Wikipedia

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in your keys
uvicorn app.main:app --host 0.0.0.0 --port 8420
```

### Configuration

All configuration is environment-driven; see [`.env.example`](.env.example) for the
full list. The ones you must set:

| Variable | Purpose |
|---|---|
| `PLANTNET_API_KEY` | Species/disease/variety identification |
| `ANTHROPIC_API_KEY` | Care-instruction generation |
| `API_BEARER_TOKEN` | Bearer token the Flutter client authenticates with |

Generate a bearer token with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

> **Set `API_BEARER_TOKEN` before exposing the service on any network.**
> When it is empty the auth check is a no-op and every endpoint is unauthenticated.
> That is intended for local development only.

Vault sync is controlled by `VAULT_SSH_HOST`: leave it as `local` to write notes
directly to `VAULT_LOCAL_PATH`, or set it to an SSH host to push to
`VAULT_REMOTE_PATH` over rsync (requires key-based auth to that host).

## API

Interactive docs are served at `/docs` once the app is running.

## License

MIT
