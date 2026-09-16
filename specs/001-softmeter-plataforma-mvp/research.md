# Research: SoftMeter — Plataforma de Metrologia de Qualidade de Software

**Feature**: 001-softmeter-plataforma-mvp | **Date**: 2026-06-24

Este documento resolve as decisões técnicas necessárias para a Phase 1, derivadas da stack
definida em ADR-003 e dos requisitos funcionais do `spec.md`.

## 1. Ingestão do código-fonte do repositório GitHub

- **Decision**: Baixar o conteúdo do repositório via o endpoint público de arquivo compactado do
  GitHub (`GET /repos/{owner}/{repo}/zipball/{ref}`), extrair em um diretório de trabalho
  temporário isolado por análise, processar, e remover o diretório ao final (sucesso ou falha).
- **Rationale**: Não exige o binário `git` no worker, funciona com requisições HTTP simples
  (`httpx`), e entrega todo o código de uma vez (mais rápido que a API de Conteúdo arquivo-a-
  arquivo para repositórios com muitos arquivos), favorecendo o orçamento de 10s do Princípio IV.
- **Alternatives considered**: (a) `git clone --depth 1` — exigiria o binário Git instalado no
  worker e tratamento de autenticação SSH/HTTPS; sem ganho relevante para repositórios públicos.
  (b) API de Conteúdo do GitHub arquivo por arquivo — número de requisições proporcional à
  quantidade de arquivos, mais lento e sujeito a limites de taxa mais cedo.

## 2. Detecção de linguagem do repositório (FR-002)

- **Decision**: Usar o endpoint `GET /repos/{owner}/{repo}/languages` do GitHub (retorna bytes
  por linguagem) no momento do cadastro; aceitar o repositório apenas se Python e/ou
  JavaScript/TypeScript estiverem entre as linguagens detectadas, e analisar apenas os arquivos
  dessas linguagens (demais arquivos são ignorados pelo motor de métricas).
- **Rationale**: É o mesmo dado que o GitHub usa para exibir a barra de linguagens no repositório,
  evitando heurísticas próprias de detecção de linguagem.
- **Alternatives considered**: Detectar linguagem apenas por extensão de arquivo após o download
  — redundante com um dado que o GitHub já expõe de forma mais confiável (ex.: arquivos gerados,
  vendor/, etc. já são excluídos pelo GitHub Linguist).

## 3. Complexidade Ciclomática, LOC e Índice de Manutenibilidade

- **Decision**: Para arquivos Python, usar **Radon** diretamente (já implementa as fórmulas
  publicadas de McCabe (1976) para Complexidade Ciclomática e de Coleman et al. (1994) para o
  Índice de Manutenibilidade, com LOC contado por SLOC lógico). Para arquivos JavaScript/
  TypeScript, usar **tree-sitter** (bindings Python via `tree-sitter-languages`) para obter a AST
  e aplicar exatamente a mesma fórmula documentada no catálogo de métricas (mesma definição de
  McCabe para nós de decisão; mesma fórmula de Coleman et al. para o Índice de Manutenibilidade),
  garantindo que a definição da métrica seja idêntica entre as duas linguagens suportadas
  (consistência exigida pelo Princípio V).
- **Rationale**: Radon é a biblioteca Python madura e testada para essas três métricas; não há
  biblioteca equivalente fora do ecossistema JS/Node para JS/TS, e introduzir um runtime Node no
  backend Python contradiz o ADR-003. `tree-sitter` permite reimplementar a mesma fórmula
  documentada sem depender de um runtime JS.
- **Alternatives considered**: Invocar uma ferramenta Node (ex.: `escomplex`) via subprocesso a
  partir do backend Python — adicionaria uma segunda runtime/dependência de sistema operacional
  ao Docker image, contrariando a simplicidade pretendida pelo ADR-003.

## 4. Acoplamento

- **Decision**: Métrica de **Instabilidade de Módulo** (`I = Ce / (Ce + Ca)`), onde `Ce`
  (Acoplamento de Saída) é o número de módulos/arquivos distintos importados por um módulo e `Ca`
  (Acoplamento de Entrada) é o número de módulos distintos que importam aquele módulo, calculada
  por arquivo e agregada por média no repositório. Implementada pelo parser AST próprio (extração
  de declarações `import`/`from...import` em Python e `import`/`require` em JS/TS via
  tree-sitter).
- **Rationale**: É uma métrica de acoplamento com definição formal e fonte bibliográfica
  amplamente citada (Robert C. Martin, *Agile Software Development: Principles, Patterns, and
  Practices*, 2002), aplicável de forma equivalente a ambas as linguagens suportadas via grafo de
  imports — exatamente o que o Princípio V exige (fórmula + fonte + limites).
- **Alternatives considered**: CBO (Coupling Between Objects, Chidamber & Kemerer, 1994) — mais
  apropriado a paradigma orientado a objetos por classe; rejeitado porque parte do código-alvo
  (especialmente JS funcional) não é estruturado em classes, tornando a métrica inconsistente
  entre repositórios.

## 5. Score de Duplicação

- **Decision**: Detecção de clones Tipo-1/Tipo-2 por *shingling* de blocos de tokens normalizados
  (identificadores e literais substituídos por placeholders), com janela mínima configurável
  (ex.: 6 linhas), usando a mesma AST do tree-sitter para tokenizar. Score = percentual de linhas
  de código duplicadas em relação ao total de linhas analisadas.
- **Rationale**: É a mesma abordagem (normalização + comparação de blocos) usada por ferramentas
  de mercado de detecção de duplicação (ex.: a métrica de "duplicated lines density" do
  SonarQube), com formato comparável e fonte documentável.
- **Alternatives considered**: Comparação textual exata linha a linha — não detecta clones Tipo-2
  (renomeação de variáveis), produzindo um score artificialmente baixo.

## 6. Cobertura de Testes (decisão confirmada com o usuário)

- **Decision**: O SoftMeter **não executa** a suíte de testes do repositório analisado. Em vez
  disso, procura artefatos de cobertura já publicados no repositório (`coverage.xml`, `lcov.info`,
  `.coverage`, badge do Codecov/Coveralls referenciado no `README`) e extrai o percentual relatado.
  Quando nenhum artefato é encontrado, a métrica é marcada como **"Não disponível"** para aquela
  análise e é excluída do índice agregado de conformidade (em vez de contar como Não-Conforme).
- **Rationale**: Executar código de terceiros arbitrário (instalar dependências e correr a suíte
  de testes de um repositório público desconhecido) é uma superfície de execução de código
  arbitrário que o projeto explicitamente decidiu não assumir nesta versão, e dificilmente caberia
  no orçamento de 10s do Princípio IV. Ler artefatos estáticos já publicados é seguro e rápido.
- **Alternatives considered**: Executar testes em sandbox isolado (rejeitado por risco de
  segurança e custo de infraestrutura); métrica proxy estática de razão teste/código (rejeitado
  por divergir do nome e do significado de "Cobertura de Testes" definidos no spec).
- **Atualização (16/09/2026, ver ADR-004)**: adicionada uma fonte antes das listadas acima — o
  artifact de cobertura mais recente publicado pelo GitHub Actions do próprio repositório
  analisado (ex.: `backend-coverage`, `frontend-coverage`), baixado sem executar nada. Motivo: a
  maioria dos repositórios públicos não versiona artefato de build (é o próprio caso do
  SoftMeter), o que deixava a métrica quase sempre "Não disponível" na prática. A decisão de
  nunca executar código do repositório analisado permanece intacta.

## 7. Processamento assíncrono e orçamento de 10 segundos (Princípio IV)

- **Decision**: A requisição de análise inicia de forma síncrona; se o cálculo das 6 métricas
  para os arquivos elegíveis (Python/JS/TS) completar em até ~8 segundos, o resultado é retornado
  diretamente. Caso o repositório seja maior (heurística: número de arquivos elegíveis acima de um
  limite configurável), a tarefa é despachada para uma fila Celery/Redis, e o endpoint retorna
  imediatamente um identificador de análise com status "processando"; o frontend faz polling até
  a conclusão.
- **Rationale**: Atende ao Princípio IV (resultado em até 10s para o caso padrão) sem impor um
  hard timeout abrupto que descartaria análises de repositórios maiores — a degradação graciosa é
  explicitamente exigida pela constituição.
- **Alternatives considered**: Sempre assíncrono (mais simples de implementar, mas penaliza a
  experiência do caso comum de repositórios pequenos, que é a maioria no contexto de um TCC).

## 8. Geração de relatório PDF

- **Decision**: ReportLab para montar o PDF diretamente no backend, com um template programático
  que inclui: identificação do repositório, data da análise, e para cada métrica — valor medido,
  fórmula, fonte bibliográfica e limites de especificação (lidos do catálogo de métricas em
  `data-model.md`), e gráfico de tendência (quando solicitado para o histórico).
- **Rationale**: Biblioteca madura, sem dependências de sistema externas (ex.: não exige um
  navegador headless), adequada a um PDF estruturado/tabular como o exigido pelo FR-009.
- **Alternatives considered**: Renderizar HTML e converter via um navegador headless (ex.:
  Playwright/Chromium) — mais pesado para um documento essencialmente tabular, e adicionaria
  outra dependência de runtime ao container do backend.

## 9. Autenticação

- **Decision**: JWT de acesso de curta duração (ex.: 15 min) + refresh token de longa duração
  (ex.: 7 dias), ambos assinados pelo backend; senhas hasheadas com bcrypt. Refresh token
  armazenado como cookie HTTPOnly; access token usado no header `Authorization: Bearer`.
- **Rationale**: Padrão de mercado para APIs FastAPI stateless, equilibra segurança (token de
  acesso de vida curta) e experiência do usuário (refresh evita logins repetidos).
- **Alternatives considered**: Sessão baseada em cookie no servidor (stateful) — exigiria estado
  de sessão compartilhado caso o backend escale horizontalmente; descartado por não haver
  exigência de escala nesta versão, mas JWT mantém a opção aberta sem custo adicional.

## 10. Testes E2E

- **Decision**: Playwright, cobrindo os fluxos críticos das User Stories 1 e 2 (cadastro →
  análise → dashboard) através da UI real do frontend Vite/React.
- **Rationale**: Suporta TypeScript nativamente, integra-se bem a um frontend Vite, e é a opção
  mais usada atualmente para E2E em aplicações React.
- **Alternatives considered**: Cypress — também viável; Playwright foi preferido por suporte
  nativo a múltiplos navegadores e melhor desempenho em pipelines de CI.

## Resumo das decisões

| # | Tópico | Decisão |
|---|---|---|
| 1 | Ingestão de código | Download de zipball via API do GitHub |
| 2 | Detecção de linguagem | Endpoint `languages` do GitHub |
| 3 | Complexidade/LOC/MI | Radon (Python) + tree-sitter com mesma fórmula (JS/TS) |
| 4 | Acoplamento | Instabilidade de Módulo (Martin, 2002) via grafo de imports |
| 5 | Duplicação | Shingling de tokens normalizados (estilo SonarQube) |
| 6 | Cobertura de Testes | Leitura de artefatos publicados; "Não disponível" se ausente |
| 7 | Performance/assincronia | Síncrono até ~8s; acima do limiar, Celery+Redis com polling |
| 8 | Relatório PDF | ReportLab |
| 9 | Autenticação | JWT (access curto + refresh longo) + bcrypt |
| 10 | E2E | Playwright |

Nenhum item de Technical Context permanece como NEEDS CLARIFICATION após esta pesquisa.
