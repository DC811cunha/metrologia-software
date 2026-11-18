# Data Model: SoftMeter — Plataforma de Metrologia de Qualidade de Software

**Feature**: 001-softmeter-plataforma-mvp | **Date**: 2026-06-24 | **Atualizado**: 2026-11-17 (versão de sessão, identidade do repositório, escopo e ajustes do catálogo — ADRs 006 a 014)

## Entidades

### Usuário

Conta autenticada, proprietária dos repositórios cadastrados e relatórios gerados (FR-010, FR-011).

| Campo | Tipo | Regras |
|---|---|---|
| id | UUID | chave primária |
| email | string | único, formato de email válido; **armazenado em minúsculas** (a comparação ignora a caixa) |
| password_hash | string | bcrypt; nunca exposto via API; a senha aceita tem de 8 a 72 bytes em UTF-8 (ADR-006) |
| token_version | inteiro | padrão 0; sobe no logout e no reset de senha, o que invalida na hora todos os JWT (access e refresh) emitidos antes (ADR-006) |
| criado_em | timestamp | definido na criação |

**Relacionamentos**: 1 Usuário → N Repositório.

---

### Repositório

Repositório GitHub público cadastrado por um usuário (FR-001, FR-002, FR-015).

| Campo | Tipo | Regras |
|---|---|---|
| id | UUID | chave primária |
| usuario_id | UUID | FK → Usuário; obrigatório |
| url | string | URL pública do GitHub; única em combinação com `usuario_id` (FR-015). Gravada como informada no cadastro e atualizada para o nome canônico na primeira análise depois de uma renomeação (ADR-014) |
| owner_nome | string | `{owner}/{repo}`; acompanha a `url` |
| github_id | inteiro (nullable) | id numérico do repositório no GitHub (nunca muda); gravado na primeira análise e usado para detectar que o nome passou a apontar para outro repositório (ADR-014). Não é exposto pela API |
| linguagens_detectadas | lista de string | obtida via endpoint `languages` do GitHub; deve interseccionar `{python, javascript, typescript}` (FR-002), senão o cadastro é rejeitado |
| status_acesso | enum: `ativo`, `inacessivel` | `inacessivel` quando o GitHub nega o acesso (403/404/451) durante uma análise — repositório privado ou excluído (FR-014). Volta a `ativo` na primeira análise em que o GitHub responde. Cota esgotada e indisponibilidade do GitHub **não** alteram o estado (ADR-013); renomeação é acompanhada, não bloqueia (ADR-014) |
| criado_em | timestamp | definido no cadastro |

**Relacionamentos**: N Repositório → 1 Usuário; 1 Repositório → N Análise; 1 Repositório → N Relatório.

**Exclusão**: remover um Repositório apaga, em cascata, suas Análises, Medições e Relatórios — e os
arquivos PDF no disco. A confirmação ao usuário é responsabilidade da interface.

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
| motivo_falha | string (nullable, até 1000) | preenchido apenas quando `status = falhou` (ex.: repositório inacessível, cota ou indisponibilidade do GitHub, repositório grande demais, nome apontando para outro repositório, prazo excedido, fila indisponível) |
| solicitada_em | timestamp | criação do registro |
| concluida_em | timestamp (nullable) | data de **término**: preenchido ao atingir `concluida` **ou `falhou`**; só `pendente`/`processando` a têm nula |
| status_conformidade_geral | enum (nullable): `Conforme`, `Condicional`, `Não-Conforme` | calculado apenas quando `status = concluida`, a partir do índice agregado das Medições com status diferente de "Não disponível" (se nenhuma tiver escore, vale `Não-Conforme`) |

**Máquina de estados**: `pendente → processando → (concluida | falhou)`. Nenhuma transição reversa.
Disparada exclusivamente por ação do usuário (FR-012) — sem agendamento automático. **Toda tentativa é
gravada**, inclusive as que falham: o histórico mostra o que aconteceu e por quê (ADR-013).

**Relacionamentos**: N Análise → 1 Repositório; 1 Análise → N Medição (uma por Métrica aplicável).

---

### Métrica (Catálogo — Princípio V)

Catálogo fixo de métricas suportadas nesta versão (FR-004, FR-013). Esta tabela é a entrada
"definição-antes-de-exibição" exigida pela constituição: nenhuma Medição pode referenciar uma
Métrica que não esteja completamente preenchida abaixo.

| Chave | Nome | Unidade | Fórmula | Fonte bibliográfica | Limite Nominal (Conforme) | Faixa Condicional | Não-Conforme |
|---|---|---|---|---|---|---|---|
| `complexidade_ciclomatica` | Complexidade Ciclomática | nº de caminhos / função (média do repositório) | `CC = E - N + 2P` (arestas - nós + 2×componentes conexos do grafo de fluxo de controle), por função/método, McCabe (1976); código de produção apenas | McCabe, T.J. (1976). *A Complexity Measure*. IEEE Trans. Software Engineering; NIST Special Publication 500-235 | ≤ 10 | 11–20 | > 20 |
| `loc` | Linhas de Código (LOC) | linhas / função (média do repositório) | Contagem de linhas físicas de código (SLOC), excluindo comentários e linhas em branco, por função/método — mesma convenção em Python e JS/TS (ADR-010) | Martin, R.C. (2008). *Clean Code* | ≤ 30 | 31–60 | > 60 |
| `indice_manutenibilidade` | Índice de Manutenibilidade | escala 0–100 (por arquivo; média do repositório **ponderada pelas linhas de código**) | `MI = 171 − 5.2·ln(HV) − 0.23·CC − 16.2·ln(LOC)` (HV = volume de Halstead), normalizado 0–100, por arquivo; a média pesa cada arquivo pelo seu SLOC (ADR-015) | Coleman, D. et al. (1994). *Using Metrics to Evaluate Software System Maintainability*. IEEE Computer; ranks adotados pela ferramenta Radon | ≥ 20 (Rank A) | 10–19,99 (Rank B) | < 10 (Rank C) |
| `cobertura_testes` | Cobertura de Testes | % de linhas cobertas | Percentual relatado em artefato de cobertura já publicado, lido nesta ordem: artifacts do GitHub Actions do run de CI mais recente — combinados por soma de linhas em monorepos (ADR-004, ADR-012) —, `coverage.xml`, `lcov.info`, badge Codecov/Coveralls no README; ver `research.md` item 6 | Especificação de cobertura de testes (ex.: relatórios `coverage.py`/`lcov`); limites de referência alinhados ao Princípio I da Constituição SoftMeter | ≥ 80% | 50%–79% | < 50% (ou **Não disponível** se nenhum artefato for encontrado) |
| `acoplamento` | Acoplamento (Instabilidade de Módulo) | razão 0–1 (média do repositório) | `I = Ce / (Ce + Ca)` — Ce = acoplamento de saída (imports internos), Ca = acoplamento de entrada (módulos que importam este); imports resolvidos por sufixo de caminho (Python) e por `tsconfig`/`jsconfig` (JS/TS). **Não disponível** se nenhum import interno for resolvido — inclusive em repositório de um único módulo (ADR-010, ADR-015) | Martin, R.C. (2002). *Agile Software Development: Principles, Patterns, and Practices* | ≤ 0,70 | 0,70–0,85 | > 0,85 |
| `score_duplicacao` | Score de Duplicação | % de linhas duplicadas | Percentual de linhas em blocos de código duplicados (Tipo-1/Tipo-2) detectados por *shingling* de tokens normalizados, janela mínima de 6 linhas com ao menos 4 linhas distintas; imports não contam e janelas sobrepostas do mesmo arquivo não casam entre si (ADR-010) | Abordagem equivalente à métrica *Duplicated Lines Density* da SonarSource (documentação pública do SonarQube) | ≤ 5% | 5%–15% | > 15% |

**Regra de status "Não disponível"**: aplica-se a `cobertura_testes`, quando nenhuma fonte de cobertura é
encontrada (artifact de CI, artefato versionado ou badge), e a `acoplamento`, quando nenhum import interno é
resolvido (ADR-010, ADR-015). Medições com esse status têm `valor_medido` nulo e são excluídas do cálculo do
`status_conformidade_geral` da Análise (não contam como Não-Conforme).

**Escopo da medição (ADR-011, ADR-012)**: as métricas de código (CC, LOC, MI, acoplamento e duplicação)
consideram apenas o código-fonte de produção em Python/JS/TS. Ficam de fora: arquivos e diretórios de teste,
dependências (`node_modules`, `venv`…), arquivos gerados/minificados (`*.min.*`, `*.d.ts`, `.next/`…), saídas de build
(`build/`, `dist/`, `out/`, `target/`, `coverage/`, quando na raiz ou ao lado de um manifesto de projeto — ADR-015)
e arquivos-fonte acima de 1 MB. A Cobertura de Testes vem dos relatórios publicados pelo repositório. A nota
de escopo aparece no dashboard e no PDF (`SCOPE_NOTE`). Um repositório só com testes não é analisável.

---

### Medição

Valor de uma Métrica específica dentro de uma Análise (FR-004, FR-005, FR-006).

| Campo | Tipo | Regras |
|---|---|---|
| id | UUID | chave primária |
| analise_id | UUID | FK → Análise; obrigatório |
| metrica_chave | string | chave de uma Métrica do catálogo (`metrics_catalog.py`); obrigatório. O catálogo é código versionado, não tabela — logo não há FK de banco, e a integridade é garantida pela aplicação |
| valor_medido | decimal (nullable) | `null` apenas quando `status_conformidade = Não disponível` |
| status_conformidade | enum: `Conforme`, `Condicional`, `Não-Conforme`, `Não disponível` | calculado comparando `valor_medido` aos limites da Métrica correspondente |

**Relacionamentos**: N Medição → 1 Análise; N Medição → 1 Métrica (catálogo, por chave — sem FK de banco).

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
| caminho_arquivo | string | localização do PDF gerado; o arquivo é apagado junto com o Repositório |

**Relacionamentos**: N Relatório → 1 Repositório; N Relatório → 1 Usuário.

**Validação**: rejeitar geração se o Repositório não tiver nenhuma Análise com
`status = concluida` (edge case do spec).

---

### Token de Redefinição de Senha *(adicionado em 16/09/2026 — ADR-005; tabela `password_reset_tokens`)*

Token de uso único para recuperação de acesso à conta (FR-016).

| Campo | Tipo | Regras |
|---|---|---|
| id | UUID | chave primária |
| usuario_id | UUID | FK → Usuário; obrigatório |
| token_hash | string (64) | hash SHA-256 do token enviado por e-mail; único; o valor bruto **nunca** é armazenado |
| expira_em | timestamp | criação + 60 min (configurável em `PASSWORD_RESET_TOKEN_EXPIRES_MINUTES`) |
| usado_em | timestamp (nullable) | preenchido quando o token é consumido; um token usado não é aceito de novo |
| criado_em | timestamp | definido na criação |

**Relacionamentos**: N Token → 1 Usuário.

**Validação**: a redefinição é recusada (HTTP 400, "Token inválido ou expirado") quando o hash não
existe, o token já foi usado, expirou ou o usuário não existe mais.

---

## Diagrama de relacionamentos (textual)

```text
Usuário (1) ───── (N) Repositório (1) ───── (N) Análise (1) ───── (N) Medição (N) ───── (1) Métrica
   │                                                                                      [catálogo fixo]
   ├────────────────────────────── (N) Relatório ─────────────────────────────────────┘
   │
   └── (1) ───── (N) Token de Redefinição de Senha
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
| Token de Redefinição de Senha | FR-016 |
| Repositório.status_acesso, Análise.motivo_falha | FR-014, FR-022 |
| Usuário.token_version | FR-010, FR-018 |
| Repositório.github_id, exclusão em cascata | FR-019, FR-020 |
