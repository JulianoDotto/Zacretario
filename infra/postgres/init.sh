#!/bin/sh
# Runs once, on the first start of an empty Postgres volume.
# Creates one user and one database per app, so each app only sees its own data.
set -eu

for app in n8n evolution zacretario n8n_teste zacretario_teste; do
  case "$app" in
    n8n) password="$N8N_DB_PASSWORD" ;;
    evolution) password="$EVOLUTION_DB_PASSWORD" ;;
    zacretario) password="$ZACRETARIO_DB_PASSWORD" ;;
    n8n_teste) password="$N8N_TESTE_DB_PASSWORD" ;;
    zacretario_teste) password="$ZACRETARIO_TESTE_DB_PASSWORD" ;;
  esac
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" \
    -v app="$app" -v password="$password" <<'SQL'
CREATE ROLE :"app" LOGIN PASSWORD :'password';
CREATE DATABASE :"app" OWNER :"app";
SQL
done
