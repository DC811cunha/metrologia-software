# Feature Specification: SoftMeter — Plataforma de Metrologia de Qualidade de Software

**Feature Branch**: `001-softmeter-plataforma-mvp`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "Desenvolver o SoftMeter, uma plataforma web de TCC que aplica metrologia industrial à qualidade de software. O sistema permite que desenvolvedores cadastrem repositórios GitHub, executem análises automáticas e visualizem métricas de qualidade como Complexidade Ciclomática, LOC, Índice de Manutenibilidade, Cobertura de Testes, Acoplamento e Score de Duplicação em um dashboard estilo gauge metrológico com valor medido, limites de especificação e status de conformidade. O sistema mantém histórico de análises para identificar tendências, gera relatórios PDF técnicos adequados para inclusão em TCC, e possui autenticação de usuários. Linguagens suportadas: Python e JavaScript/TypeScript. Repositórios GitHub públicos apenas nesta versão."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cadastro de repositório e execução de análise automática (Priority: P1)

Um desenvolvedor cadastra um repositório GitHub público e solicita que o sistema execute uma
análise automática, coletando as métricas de qualidade do código.

**Why this priority**: É o ponto de entrada de todo o valor do produto — sem registrar um
repositório e gerar uma medição, nenhuma outra funcionalidade (dashboard, histórico, relatório)
tem dados para operar.

**Independent Test**: Pode ser totalmente testado cadastrando a URL de um repositório GitHub
público com código Python ou JavaScript/TypeScript, disparando uma análise e confirmando que um
conjunto completo de métricas é calculado e armazenado.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado sem repositórios cadastrados, **When** ele informa a URL de
   um repositório GitHub público válido, **Then** o sistema cadastra o repositório e permite
   disparar uma análise automática sobre ele.
2. **Given** um repositório cadastrado, **When** o usuário solicita uma análise, **Then** o
   sistema calcula Complexidade Ciclomática, LOC, Índice de Manutenibilidade, Cobertura de
   Testes, Acoplamento e Score de Duplicação para o código-fonte e armazena o resultado como um
   novo registro de análise.
3. **Given** um repositório cujo código é escrito apenas em uma linguagem não suportada,
   **When** o usuário tenta cadastrá-lo, **Then** o sistema rejeita o cadastro informando que
   apenas Python e JavaScript/TypeScript são suportados nesta versão.

---

### User Story 2 - Visualização de métricas em dashboard estilo gauge metrológico (Priority: P1)

Um desenvolvedor visualiza o resultado da análise mais recente de um repositório como um
conjunto de gauges metrológicos, cada um mostrando o valor medido, os limites de especificação e
o status de conformidade da métrica correspondente.

**Why this priority**: É a proposta de valor central do projeto — apresentar qualidade de
software com o mesmo rigor visual de um laudo de inspeção industrial. Sem isso, a análise
calculada na User Story 1 não tem utilidade percebida pelo usuário.

**Independent Test**: Com pelo menos uma análise concluída, abrir o dashboard do repositório
deve exibir um gauge por métrica com valor, limites e status — testável de forma independente
do histórico ou do relatório PDF.

**Acceptance Scenarios**:

1. **Given** um repositório com ao menos uma análise concluída, **When** o usuário abre seu
   dashboard, **Then** cada métrica é exibida como um gauge com valor medido, limites de
   especificação (nominal/superior/inferior) e status de conformidade (Conforme, Condicional ou
   Não-Conforme).
2. **Given** uma métrica cujo valor medido está fora dos limites de especificação, **When** ela
   é exibida no dashboard, **Then** o gauge indica visualmente Não-Conforme (ou Condicional,
   conforme a faixa), de forma consistente com a classificação de conformidade do projeto.

---

### User Story 3 - Histórico de análises e identificação de tendências (Priority: P2)

Um desenvolvedor compara várias execuções de análise ao longo do tempo para verificar se as
métricas de um repositório estão melhorando ou piorando.

**Why this priority**: Agrega valor relevante para a narrativa de evolução contínua de
qualidade (central no TCC), mas depende de já existir análise e dashboard funcionando (US1/US2).

**Independent Test**: Com duas ou mais análises registradas para o mesmo repositório, a tela de
histórico deve exibir a lista cronológica e a tendência de cada métrica.

**Acceptance Scenarios**:

1. **Given** um repositório com múltiplas análises concluídas, **When** o usuário abre a tela de
   histórico, **Then** ele vê cada análise passada com sua data e valores de métricas, em ordem
   cronológica.
2. **Given** um repositório com ao menos duas análises, **When** o usuário visualiza a tendência
   de uma métrica específica, **Then** o sistema indica se essa métrica melhorou, piorou ou
   permaneceu estável entre as execuções.

---

### User Story 4 - Geração de relatório técnico em PDF (Priority: P2)

Um desenvolvedor gera um relatório em PDF de uma análise, adequado para inclusão como evidência
técnica em um Trabalho de Conclusão de Curso.

**Why this priority**: É um entregável importante para o contexto acadêmico do projeto, mas só
tem sentido depois que dashboard e histórico já existem e contêm dados reais.

**Independent Test**: A partir de uma análise concluída, gerar o relatório PDF e confirmar que
ele contém definição, valor, limites e status de conformidade de cada métrica.

**Acceptance Scenarios**:

1. **Given** uma análise concluída, **When** o usuário solicita um relatório PDF, **Then** o
   sistema gera um documento para download contendo identificação do repositório, data da
   análise, valor medido de cada métrica, limites de especificação, status de conformidade e a
   fonte bibliográfica que sustenta a definição de cada métrica.
2. **Given** um repositório com histórico de análises, **When** o usuário solicita um relatório
   do histórico completo, **Then** o documento inclui adicionalmente a tendência de cada métrica
   ao longo das análises.

---

### User Story 5 - Autenticação de usuários (Priority: P3)

Um visitante cria uma conta e faz login para gerenciar seus próprios repositórios e análises.

**Why this priority**: É necessário para qualquer uso real multiusuário da plataforma, mas o
valor central de metrologia (US1-US4) pode ser demonstrado e validado mesmo com uma única conta;
por isso fica priorizado depois das funcionalidades centrais.

**Independent Test**: Um novo visitante consegue se cadastrar, fazer login e visualizar apenas
os repositórios que ele próprio cadastrou.

**Acceptance Scenarios**:

1. **Given** um novo visitante, **When** ele se cadastra com email e senha, **Then** uma conta é
   criada e ele é autenticado automaticamente.
2. **Given** um usuário já cadastrado, **When** ele faz login com credenciais corretas, **Then**
   ele recupera acesso aos repositórios e análises que cadastrou anteriormente.
3. **Given** um visitante não autenticado, **When** ele tenta acessar o dashboard ou o cadastro
   de repositórios, **Then** ele é redirecionado para a tela de login/cadastro.

---

### Edge Cases

- O que acontece quando um repositório cadastrado se torna privado, é renomeado ou é excluído no
  GitHub entre o cadastro e uma nova execução de análise?
- Como o sistema deve se comportar quando um repositório mistura código em linguagens suportadas
  (Python/JS/TS) e não suportadas — analisa apenas a parte suportada ou rejeita o cadastro por
  completo?
- O que acontece quando a API do GitHub está indisponível ou com limite de requisições excedido
  durante uma análise?
- O que acontece quando um repositório não possui nenhum teste automatizado (cobertura de testes
  não pode ser calculada)?
- O que acontece quando o usuário solicita um relatório PDF para um repositório que ainda não
  possui nenhuma análise concluída?
- Como o sistema deve tratar o cadastro repetido da mesma URL de repositório pelo mesmo usuário,
  ou por usuários diferentes?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que um usuário autenticado cadastre um repositório GitHub
  público informando sua URL.
- **FR-002**: O sistema DEVE validar que a(s) linguagem(ns) principal(is) do repositório
  cadastrado seja(m) Python e/ou JavaScript/TypeScript, rejeitando o cadastro com mensagem clara
  caso contrário.
- **FR-003**: O sistema DEVE permitir que o usuário dispare uma execução de análise automática
  para qualquer repositório que tenha cadastrado.
- **FR-004**: O sistema DEVE calcular, em cada execução de análise, as métricas: Complexidade
  Ciclomática, LOC, Índice de Manutenibilidade, Cobertura de Testes, Acoplamento e Score de
  Duplicação.
- **FR-005**: O sistema DEVE comparar o valor medido de cada métrica com seus limites de
  especificação documentados e classificá-la como Conforme, Condicional ou Não-Conforme.
- **FR-006**: O sistema DEVE exibir os resultados da análise em um dashboard no formato de gauge
  metrológico, mostrando para cada métrica: valor medido, limites de especificação e status de
  conformidade.
- **FR-007**: O sistema DEVE persistir cada execução de análise como um registro histórico
  associado ao seu repositório, incluindo data/hora e todos os valores de métricas calculados.
- **FR-008**: O sistema DEVE permitir que o usuário visualize a sequência histórica de análises
  de um repositório e a tendência (melhora/piora/estável) de cada métrica entre execuções.
- **FR-009**: O sistema DEVE permitir que o usuário gere um relatório em PDF de uma análise,
  contendo: identificação do repositório, data da análise, valor medido de cada métrica, limites
  de especificação, status de conformidade e a fonte bibliográfica que sustenta a definição da
  métrica.
- **FR-010**: O sistema DEVE exigir que o usuário esteja autenticado (conta criada e login
  realizado) antes de cadastrar repositórios ou visualizar dashboards, histórico ou relatórios.
- **FR-011**: O sistema DEVE restringir os repositórios, análises e relatórios de cada usuário à
  visibilidade exclusiva da própria conta (sem acesso a dados de outros usuários).
- **FR-012**: O sistema DEVE permitir disparar uma análise exclusivamente por ação explícita do
  usuário (sob demanda), sem agendamento automático ou execução em segundo plano nesta versão.
- **FR-013**: O sistema DEVE definir, para cada métrica suportada, limites de especificação fixos
  (valores nominal, superior e inferior) baseados em literatura/normas reconhecidas, aplicados
  igualmente a todos os repositórios analisados nesta versão; o sistema NÃO permite customização
  desses limites por usuário ou por repositório nesta versão.
- **FR-014**: O sistema DEVE rejeitar tentativas de análise sobre repositórios inacessíveis
  (privados, renomeados ou excluídos), informando ao usuário o motivo da falha.
- **FR-015**: O sistema DEVE impedir o cadastro duplicado da mesma URL de repositório dentro da
  conta do mesmo usuário.

### Key Entities

- **Usuário**: conta autenticada, proprietária dos repositórios cadastrados e relatórios
  gerados; possui identificador, email, credenciais e a lista de repositórios próprios.
- **Repositório**: repositório GitHub público cadastrado por um usuário; possui URL, nome,
  linguagem(ns) detectada(s), data de cadastro e o usuário proprietário.
- **Análise**: execução pontual de medição sobre um repositório; possui data/hora, repositório
  associado, o conjunto de medições por métrica e um status de conformidade geral.
- **Métrica**: tipo de medição metrológica suportado pela plataforma (Complexidade Ciclomática,
  LOC, Índice de Manutenibilidade, Cobertura de Testes, Acoplamento, Score de Duplicação);
  possui nome, unidade, fórmula, fonte bibliográfica e limites de especificação fixos
  (nominal/superior/inferior).
- **Medição**: valor de uma métrica específica dentro de uma análise; possui a métrica de
  referência, o valor medido e o status de conformidade (Conforme/Condicional/Não-Conforme).
- **Relatório**: documento PDF gerado a partir de uma ou mais análises de um repositório; possui
  a(s) análise(s) referenciada(s), data de geração e o conteúdo completo (métricas, limites,
  status, fontes bibliográficas).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um novo usuário consegue cadastrar um repositório GitHub público e obter o
  primeiro conjunto completo de métricas em até 10 segundos para um repositório de porte
  pequeno/médio.
- **SC-002**: 90% dos usuários de primeira utilização conseguem identificar o status de
  conformidade de qualquer métrica individual no dashboard sem explicação adicional.
- **SC-003**: Usuários conseguem consultar um histórico com pelo menos 10 análises de um mesmo
  repositório e identificar se a tendência de uma métrica está melhorando ou piorando em até 30
  segundos após abrir a tela de histórico.
- **SC-004**: Em 100% dos relatórios PDF gerados, todas as métricas exibidas incluem definição
  formal, fórmula, fonte bibliográfica e limites de especificação, sem campos ausentes.
- **SC-005**: Em 100% das tentativas de cadastro de repositórios com linguagem fora do escopo
  suportado (diferente de Python/JS/TS), o cadastro é rejeitado com explicação clara ao usuário.
- **SC-006**: Em nenhuma sessão de uso um usuário autenticado consegue visualizar repositórios,
  análises ou relatórios pertencentes a outra conta (zero vazamento de dados entre contas).

## Assumptions

- A autenticação usa um modelo padrão de conta com email e senha (sessão ou token), sem exigir
  SSO corporativo, por se tratar de uma plataforma acadêmica de uso individual.
- O cadastro de repositório exige apenas a URL pública do GitHub; nenhuma autenticação adicional
  com o GitHub (token/OAuth) é necessária nesta versão, já que somente repositórios públicos são
  suportados.
- Cada execução de análise processa o conteúdo do repositório no momento da execução, sem
  exigência de sincronização contínua entre execuções; cada execução é uma "medição"
  independente no tempo.
- Não há limite definido para a quantidade de repositórios ou análises por usuário nesta versão.
- O relatório PDF pode ser gerado tanto para uma análise individual quanto, opcionalmente, para o
  histórico completo de um repositório, sem exigência de um template institucional específico
  além de conter os dados metrológicos completos.
- A classificação geral de conformidade (Conforme ≥ 90%, Condicional 70–89%, Não-Conforme < 70%)
  segue o critério já documentado no projeto, aplicada a um índice agregado calculado a partir do
  status individual de cada métrica.
