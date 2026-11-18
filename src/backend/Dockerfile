# Imagem do backend com dois alvos:
#   - dev  (padrão, o último estágio): extras de teste, código montado por volume e --reload;
#   - prod (`target: prod` no docker-compose.prod.yml): só as dependências de execução, sem --reload e
#     rodando como usuário comum (não root).
# As versões vêm do requirements.txt (constraints), para o build ser reprodutível.

FROM python:3.15-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt ./


FROM base AS prod

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
RUN pip install --no-cache-dir -c requirements.txt . && rm -rf build *.egg-info

# Usuário sem privilégios; o diretório dos PDFs é criado já com o dono certo para que o volume nomeado
# montado nele (docker-compose.prod.yml) herde a permissão na primeira vez.
RUN useradd --system --uid 10001 --create-home softmeter \
    && mkdir -p /app/generated_reports \
    && chown -R softmeter:softmeter /app/generated_reports
USER softmeter

EXPOSE 3001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001", "--proxy-headers"]


FROM base AS dev

RUN pip install --no-cache-dir -c requirements.txt -e ".[dev]"

COPY . .

EXPOSE 3001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001", "--reload"]
