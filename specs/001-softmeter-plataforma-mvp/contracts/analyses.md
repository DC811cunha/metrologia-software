# Contract: Análises

**Feature**: 001-softmeter-plataforma-mvp | Requisitos: FR-003 a FR-008, FR-012, FR-014, US1, US2, US3

Base path: `/api/v1/repositories/{repository_id}/analyses` (autenticado; repositório deve
pertencer ao usuário — FR-011)

## POST /api/v1/repositories/{repository_id}/analyses

Dispara uma nova análise sob demanda (FR-003, FR-012 — sem agendamento automático).

**Comportamento**: baixa o conteúdo do repositório (ver `research.md` item 1), calcula as 6
métricas do catálogo (`data-model.md`); se o tamanho do repositório estiver dentro do orçamento
síncrono, retorna o resultado completo; caso contrário, retorna `status: processando` e a análise
é concluída de forma assíncrona via Celery/Redis (Princípio IV).

**Responses**:
- `201 Created`, corpo com `status: concluida` → objeto Análise completo com as 6 Medições
- `202 Accepted`, corpo com `status: processando` → `{ "id": "uuid", "status": "processando" }`
- `404 Not Found` → repositório não existe ou não pertence ao usuário
- `409 Conflict` → repositório está `inacessivel` (FR-014); corpo inclui `motivo_falha`

## GET /api/v1/repositories/{repository_id}/analyses/{analysis_id}

Consulta o status/resultado de uma análise (usado para polling enquanto `status = processando`).

**Responses**:
- `200 OK` → objeto Análise (`status`, e se `concluida`: `status_conformidade_geral` e lista de
  Medições com `metrica_chave`, `valor_medido`, `status_conformidade`; se `falhou`: `motivo_falha`)
- `404 Not Found`

## GET /api/v1/repositories/{repository_id}/analyses

Lista o histórico de análises do repositório, ordenado cronologicamente (FR-008, US3).

**Query params**: `?metrica={chave}` (opcional) para retornar apenas a série temporal de uma
métrica específica, incluindo o campo calculado `tendencia: melhorando | piorando | estavel`
(comparando a análise mais recente com a anterior).

**Responses**:
- `200 OK` → `[{ "id": "uuid", "concluida_em": "timestamp", "status_conformidade_geral": "...", "medicoes": [...] }]`
