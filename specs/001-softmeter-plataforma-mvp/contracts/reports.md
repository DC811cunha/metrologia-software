# Contract: Relatórios

**Feature**: 001-softmeter-plataforma-mvp | Requisitos: FR-009, US4

Base path: `/api/v1/repositories/{repository_id}/reports` (autenticado; repositório deve
pertencer ao usuário)

*(Atualizado em 17/11/2026 — ADR-012; reflete o comportamento atual.)* Sem token válido → `401
{"detail": "Não autenticado"}`; erros de negócio têm o corpo `{"detail": "<mensagem>"}`; `id` que não é
UUID ou corpo malformado → `422` com `detail` em lista (formato FastAPI).

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
`data-model.md`), conforme FR-009, e a **nota de escopo da medição** (ADR-012: só código de produção;
testes, código gerado e minificados ficam de fora). Considera apenas análises **concluídas**.
Quando `tipo = historico_completo`, inclui todas elas e a **tendência** de cada métrica, calculada entre
as duas análises mais recentes.

**Responses**:
- `201 Created` → `{ "id": "uuid", "tipo": "analise_unica", "gerado_em": "timestamp", "download_url": "string" }`
- `404 Not Found` → `"Repositório não encontrado"` (não existe ou não pertence ao usuário)
- `422 Unprocessable Entity` (`detail` em texto):
  - `analise_unica` sem `analise_id` → `"analise_id é obrigatório para tipo=analise_unica"`;
  - análise inexistente, de outro repositório ou que não está `concluida` →
    `"Análise inexistente ou não concluída"`;
  - `historico_completo` sem nenhuma análise concluída →
    `"Repositório não possui nenhuma análise concluída"` (edge case do spec);
  - `tipo` fora dos valores aceitos → `"Tipo 'xyz' desconhecido"`

## GET /api/v1/repositories/{repository_id}/reports/{report_id}/download

Faz o download do arquivo PDF gerado.

**Responses**:
- `200 OK` — `Content-Type: application/pdf` e
  `Content-Disposition: attachment; filename="softmeter-relatorio-{report_id}.pdf"`
- `404 Not Found`:
  - `"Relatório não encontrado"` → não existe, pertence a **outro repositório** ou a outro usuário;
  - `"Arquivo do relatório não encontrado"` → o registro existe, mas o PDF não está mais no disco

## Ciclo de vida

Os relatórios são apagados — registro **e** arquivo PDF — quando o repositório é excluído
(`DELETE /repositories/{id}`, ver `repositories.md`); a partir daí o download responde `404`.
