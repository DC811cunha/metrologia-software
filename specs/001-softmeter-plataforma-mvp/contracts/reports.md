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

**Comportamento**: monta o *Laudo de Conformidade de Software* em PDF via ReportLab (`research.md` item 8).
Considera apenas análises **concluídas** e mostra datas no horário de Brasília e números no formato
brasileiro (vírgula decimal). Cada página tem cabeçalho da marca e rodapé "Página X de Y".

**Análise única** (`analise_unica`):
- identificação: repositório, linguagens detectadas, id e data da análise;
- **veredito**: status geral, **índice de conformidade (0–100)** com a barra de faixas (70/90) e a contagem de
  métricas por status; quando há análise concluída anterior do mesmo repositório, a **variação do índice** e a
  coluna "vs. anterior" (melhorou/piorou/estável) em cada métrica;
- **quadro de medições** com valor e unidade, posição do valor nas faixas de especificação (medidor desenhado)
  e status;
- **resumo interpretativo**: pontos fortes, pontos de atenção (com a implicação prática, **quanto falta para
  chegar a Conforme** e uma sugestão de ação genérica) e métricas não avaliadas; a conta do índice agregado;
- **ficha técnica** de cada métrica (definição/fórmula, fonte bibliográfica e faixas com o **sentido correto** de
  cada limite: `≤` onde menos é melhor, `≥` onde mais é melhor), conforme FR-009;
- "Como ler este laudo" (faixas, índice, **nota de escopo da medição** — ADR-012 — e limitações) e referências.

**Histórico completo** (`historico_completo`): inclui todas as análises concluídas e acrescenta, antes do
restante, o período e o total de análises, o **gráfico de evolução do índice**, a tabela **variação por
métrica** (primeira × mais recente, e a tendência entre as duas mais recentes), um **gráfico por métrica** e a
**matriz de análises** (valor e status de cada métrica em cada análise, com o id completo). O resumo e a ficha
técnica referem-se à análise mais recente.

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
