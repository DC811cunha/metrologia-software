#!/usr/bin/env bash
# Atualiza a aplicação no servidor de produção: puxa o código, reconstrói as imagens, aplica as migrations e
# (re)inicia os serviços. Rode na raiz do repositório clonado no servidor, onde está o .env de produção.
#
#   ./scripts/deploy.sh
#
# Se algo falhar, nada fica pela metade: as migrations rodam ANTES de trocar os containers e o script para no
# primeiro erro. Para voltar a uma versão anterior: `git checkout <commit>` e rode o script de novo.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Erro: .env não encontrado em $(pwd). Crie-o a partir do .env.example (ver docs/deploy/roteiro-deploy-aws.md)." >&2
  exit 1
fi

compose() { docker compose -f docker-compose.prod.yml "$@"; }

echo "==> Atualizando o código"
git pull --ff-only

echo "==> Construindo as imagens (backend, worker e frontend)"
compose build

echo "==> Aplicando as migrations do banco"
compose run --rm backend alembic upgrade head

echo "==> Iniciando os serviços"
compose up -d --remove-orphans

echo "==> Aguardando a API responder"
site=$(grep -E '^SITE_ADDRESS=' .env | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'")
for _ in $(seq 1 30); do
  if curl -fsS -k --max-time 5 --resolve "${site}:443:127.0.0.1" "https://${site}/health" >/dev/null 2>&1; then
    echo "OK: https://${site}/health respondeu."
    compose ps
    exit 0
  fi
  sleep 2
done

echo "Erro: a API não respondeu em https://${site}/health. Veja: docker compose -f docker-compose.prod.yml logs --tail=100" >&2
compose ps
exit 1
