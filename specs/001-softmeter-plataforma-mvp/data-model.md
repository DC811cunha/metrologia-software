# Data Model: SoftMeter — Plataforma de Metrologia de Qualidade de Software

**Feature**: 001-softmeter-plataforma-mvp | **Date**: 2026-06-24

## Entidades

### Usuário

Conta autenticada, proprietária dos repositórios cadastrados e relatórios gerados (FR-010, FR-011).

| Campo | Tipo | Regras |
|---|---|---|
| id | UUID | chave primária |
| email | string | único, formato de email válido |
| password_hash | string | bcrypt; nunca exposto via API |
| criado_em | timestamp | definido na criação |

**Relacionamentos**: 1 Usuário → N Repositório.

---

### Repositório

Repositório GitHub público cadastrado por um usuário (FR-001, FR-002, FR-015).

| Campo | Tipo | Regras |
|---|---|---|
| id | UUID | chave primária |
| usuario_id | UUID | FK → Usuário; obrigatório |
| url | string | URL pública do GitHub; única em combinação com `usuario_id` (FR-015) |
| owner_nome | string | extraído da URL (`{owner}/{repo}`) |
| linguagens_detectadas | lista de string | obtida via endpoint `languages` do GitHub; deve interseccionar `{python, javascript, typescript}` (FR-002), senão o cadastro é rejeitado |
| status_acesso | enum: `ativo`, `inacessivel` | `inacessivel` quando o repositório se torna privado/excluído/renomeado após o cadastro (FR-014) |
| criado_em | timestamp | definido no cadastro |

**Relacionamentos**: N Repositório → 1 Usuário; 1 Repositório → N Análise.

**Validação**: rejeitar cadastro se `linguagens_detectadas` não contiver Python nem
JavaScript/TypeScript (FR-002); rejeitar cadastro se já existir um Repositório com a mesma `url`
para o mesmo `usuario_id` (FR-015).

---

### Análise

Execução pontual de medição sobre um Repositório (FR-003, FR-004, FR-007).

| Campo | Tipo | Regras |
|---|---|---|
| id | UUID | chave primária |
| repositorio_id | UUID | FK → Repositório; obrigatório |
| status | enum | `pendente` → `processando` → `concluida` \| `falhou` |
| motivo_falha | string (nullable) | preenchido apenas quando `status = falhou` (ex.: repositório inacessível, limite de API do GitHub excedido) |
| solicitada_em | timestamp | criação do registro |
| concluida_em | timestamp (nullable) | preenchido ao atingir `concluida` ou `falhou` |
| status_conformidade_geral | enum (nullable): `Conforme`, `Condicional`, `Não-Conforme` | calculado apenas quando `status = concluida`, a partir do índice agregado das Medições com status diferente de "Não disponível" |

**Máquina de estados**: `pendente → processando → (concluida | falhou)`. Nenhuma transição reversa.
Disparada exclusivamente por ação do usuário (FR-012) — sem agendamento automático.

**Relacionamentos**: N Análise → 1 Repositório; 1 Análise → N Medição (uma por Métrica aplicável).

---

### Métrica (Catálogo — Princípio V)

Catálogo fixo de métricas suportadas nesta versão (FR-004, FR-013). Esta tabela é a entrada
"definição-antes-de-exibição" exigida pela constituição: nenhuma Medição pode referenciar uma
Métrica que não esteja completamente preenchida abaixo.

| Chave | Nome | Unidade | Fórmula | Fonte bibliográfica | Limite Nominal (Conforme) | Faixa Condicional | Não-Conforme |
|---|---|---|---|---|---|---|---|
| `complexidade_ciclomatica` | Complexidade Ciclomática | nº de caminhos / função (média do repositório) | `CC = E - N + 2P` (arestas - nós + 2×componentes conexos do grafo de fluxo de controle), por função/método, McCabe (1976) | McCabe, T.J. (1976). *A Complexity Measure*. IEEE Trans. Software Engineering; NIST Special Publication 500-235 | ≤ 10 | 11–20 | > 20 |
| `loc` | Linhas de Código (LOC) | linhas / função (média do repositório) | Contagem de linhas de código lógicas (SLOC), excluindo comentários e linhas em branco, por função/método | Martin, R.C. (2008). *Clean Code* | ≤ 30 | 31–60 | > 60 |
| `indice_manutenibilidade` | Índice de Manutenibilidade | escala 0–100 (por arquivo, média do repositório) | `MI = 171 − 5.2·ln(HV) − 0.23·CC − 16.2·ln(LOC)` (HV = volume de Halstead), normalizado 0–100 | Coleman, D. et al. (1994). *Using Metrics to Evaluate Software System Maintainability*. IEEE Computer; ranks adotados pela ferramenta Radon | ≥ 20 (Rank A) | 10–19,99 (Rank B) | < 10 (Rank C) |
| `cobertura_testes` | Cobertura de Testes | % de linhas cobertas | Percentual relatado em artefato de cobertura já publicado no repositório (`coverage.xml`, `lcov.info`, badge Codecov/Coveralls); ver `research.md` item 6 | Especificação de cobertura de testes (ex.: relatórios `coverage.py`/`lcov`); limites de referência alinhados ao Princípio I da Constituição SoftMeter | ≥ 80% | 50%–79% | < 50% (ou **Não disponível** se nenhum artefato for encontrado) |
| `acoplamento` | Acoplamento (Instabilidade de Módulo) | razão 0–1 (média do repositório) | `I = Ce / (Ce + Ca)` — Ce = acoplamento de saída (imports), Ca = acoplamento de entrada (módulos que importam este) | Martin, R.C. (2002). *Agile Software Development: Principles, Patterns, and Practices* | ≤ 0,70 | 0,70–0,85 | > 0,85 |
| `score_duplicacao` | Score de Duplicação | % de linhas duplicadas | Percentual de linhas em blocos de código duplicados (Tipo-1/Tipo-2) detectados por *shingling* de tokens normalizados, janela mínima de 6 linhas | Abordagem equivalente à métrica *Duplicated Lines Density* da SonarSource (documentação pública do SonarQube) | ≤ 5% | 5%–15% | > 15% |

**Regra de status "Não disponível"**: aplica-se apenas a `cobertura_testes`, quando nenhum
artefato de cobertura é encontrado no repositório. Medições com esse status são excluídas do
cálculo do `status_conformidade_geral` da Análise (não contam como Não-Conforme).

---

### Medição

Valor de uma Métrica específica dentro de uma Análise (FR-004, FR-005, FR-006).

| Campo | Tipo | Regras |
|---|---|---|
| id | UUID | chave primária |
| analise_id | UUID | FK → Análise; obrigatório |
| metrica_chave | string | FK → Métrica (catálogo); obrigatório |
| valor_medido | decimal (nullable) | `null` apenas quando `status_conformidade = Não disponível` |
| status_conformidade | enum: `Conforme`, `Condicional`, `Não-Conforme`, `Não disponível` | calculado comparando `valor_medido` aos limites da Métrica correspondente |

**Relacionamentos**: N Medição → 1 Análise; N Medição → 1 Métrica (catálogo).

**Validação**: para cada Análise com `status = concluida`, deve existir exatamente uma Medição
por chave de Métrica do catálogo (6 no total nesta versão).

---

### Relatório

Documento PDF gerado a partir de uma ou mais Análises de um Repositório (FR-009).

| Campo | Tipo | Regras |
|---|---|---|
| id | UUID | chave primária |
| usuario_id | UUID | FK → Usuário solicitante (deve ser o proprietário do Repositório) |
| repositorio_id | UUID | FK → Repositório |
| tipo | enum: `analise_unica`, `historico_completo` | define o conteúdo incluído |
| analise_id | UUID (nullable) | obrigatório quando `tipo = analise_unica`; ignorado quando `historico_completo` (usa todas as Análises concluídas do Repositório) |
| gerado_em | timestamp | momento da geração |
| caminho_arquivo | string | localização do PDF gerado |

**Relacionamentos**: N Relatório → 1 Repositório; N Relatório → 1 Usuário.

**Validação**: rejeitar geração se o Repositório não tiver nenhuma Análise com
`status = concluida` (edge case do spec).

---

## Diagrama de relacionamentos (textual)

```text
Usuário (1) ───── (N) Repositório (1) ───── (N) Análise (1) ───── (N) Medição (N) ───── (1) Métrica
   │                                                                                      [catálogo fixo]
   └────────────────────────────── (N) Relatório ─────────────────────────────────────┘
```

## Mapeamento para Requisitos Funcionais

| Entidade/Regra | Requisitos atendidos |
|---|---|
| Repositório.linguagens_detectadas | FR-002 |
| Repositório.url + usuario_id (unicidade) | FR-015 |
| Análise (máquina de estados, disparo manual) | FR-003, FR-007, FR-012 |
| Métrica (catálogo) | FR-004, FR-013, Princípio V |
| Medição.status_conformidade | FR-005, FR-006 |
| Relatório | FR-009 |
| Usuário (escopo de dados) | FR-010, FR-011 |
| Repositório.status_acesso, Análise.motivo_falha | FR-014 |
