# Contract: Relatórios

**Feature**: 001-softmeter-plataforma-mvp | Requisitos: FR-009, US4

Base path: `/api/v1/repositories/{repository_id}/reports` (autenticado; repositório deve
pertencer ao usuário)

## POST /api/v1/repositories/{repository_id}/reports

Gera um relatório PDF.

**Request body**:
```json
{ "tipo": "analise_unica", "analise_id": "uuid" }
```
ou
```json
{ "tipo": "historico_completo" }
```

**Comportamento**: monta o PDF via ReportLab (`research.md` item 8) contendo, para cada métrica:
valor medido, fórmula, fonte bibliográfica e limites de especificação (lidos do catálogo em
`data-model.md`), conforme FR-009; quando `tipo = historico_completo`, inclui também a tendência
de cada métrica ao longo das análises.

**Responses**:
- `201 Created` → `{ "id": "uuid", "tipo": "analise_unica", "gerado_em": "timestamp", "download_url": "string" }`
- `404 Not Found` → repositório não existe ou não pertence ao usuário
- `422 Unprocessable Entity` → `tipo = analise_unica` sem `analise_id`, ou repositório sem
  nenhuma análise concluída (edge case do spec)

## GET /api/v1/repositories/{repository_id}/reports/{report_id}/download

Faz o download do arquivo PDF gerado.

**Responses**:
- `200 OK` (`Content-Type: application/pdf`)
- `404 Not Found`
