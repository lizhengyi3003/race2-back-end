# Production

Source: `lizhengyi3003/race2-back-end`, main. Managed checkout: `/srv/race3/backend`.
Use `docker-compose.production.yml`; the local development Compose files do not configure production.
Secrets live in `/etc/race3/production.env` (root, mode 600), never in GitHub source or Docker image layers.

The stack contains FastAPI plus the admin UI, MySQL 8 and go-captcha-service.
Only `127.0.0.1:8000` is published. Cloudflare Tunnel forwards
`backend.intellicoretech.cn` to that listener; the frontend Worker forwards `/api/*` and `/admin/*`.
`/healthz` checks database connectivity; `/docs`, `/redoc` and `/openapi.json` are disabled in production.

Initial provisioning runs `scripts/bootstrap_production.py` against the new database.
It imports the 3023-indicator catalogue from `deploy/indicators.xlsx`, copied from the frontend's
current 15-column source. Existing indicator configurations are preserved on subsequent deployments.
Update both copies together and review indicator changes before migrating an existing database.
AI review remains disabled until a server-owned API key and model are configured.
Automatic model training is disabled in production; train and verify models explicitly from the admin UI.

## Continuous delivery

`Backend CI` runs MySQL-backed tests and builds/lints the admin UI. A successful main push
triggers `Deploy production` for the exact tested SHA. Deployment has a concurrency lock and
waits for health checks. Actions then checks the public Tunnel origin and the same-origin dashboard
API through the Worker. The SSH key is restricted to the deployment wrapper; the host key is pinned.

GitHub production environment/repository configuration:

- Variables: `SERVER_HOST`, `SERVER_USER`.
- Secrets: `DEPLOY_SSH_KEY`, `SERVER_KNOWN_HOSTS`.
- Default Actions permissions: read-only; PR approvals by Actions disabled.
- Main requires an approving review and the `test`, `admin` and configured CodeQL checks.
  Force pushes and branch deletion are disabled.

`deploy-backend.sh main <SHA>` rebuilds the backend without removing volumes or reimporting
existing indicators. It accepts only a SHA already contained in origin/main.
To roll back code, revert the change in a new reviewed main commit and use the same entry point.
Code rollback does not reverse database migrations or restore deleted data.

The initial 2026-11-10 replacement explicitly deletes the legacy race production/development data
without backup at the owner's request. Future deployments preserve the new race3 database and volumes.
