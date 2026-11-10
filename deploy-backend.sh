#!/usr/bin/env bash
set -euo pipefail
if [[ ${SSH_ORIGINAL_COMMAND:-} =~ ^deploy-backend\.sh\ main\ ([a-f0-9]{40})$ ]]; then
  revision=${BASH_REMATCH[1]}
elif [[ ${1:-} == main && ${2:-} =~ ^[a-f0-9]{40}$ ]]; then
  revision=$2
else
  echo 'Expected: deploy-backend.sh main <40-character commit SHA>' >&2
  exit 2
fi
exec 9>/run/lock/race3-deploy.lock
flock -n 9 || { echo 'Another deployment is running' >&2; exit 1; }
cd /srv/race3/backend
[[ $(git remote get-url origin) == https://github.com/lizhengyi3003/race2-back-end.git ]]
git fetch origin main
git merge-base --is-ancestor "$revision" origin/main
if [[ $revision != $(git rev-parse origin/main) ]]; then
  echo 'Skipping superseded revision; only current main may deploy.'
  exit 0
fi
git reset --hard "$revision"
compose=(docker compose --env-file /etc/race3/production.env -f docker-compose.production.yml)
"${compose[@]}" build backend
"${compose[@]}" up -d go-captcha-service
"${compose[@]}" up -d mysql --wait --wait-timeout 180
"${compose[@]}" run --rm --no-deps backend python scripts/bootstrap_production.py
"${compose[@]}" up -d --no-deps backend --wait --wait-timeout 180
curl --fail --silent --show-error http://127.0.0.1:8000/healthz
echo "Deployed $revision"
