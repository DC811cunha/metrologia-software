# RFC-001: SoftMeter — Plataforma de Metrologia de Software

**Engenharia de Software – Católica SC**

---

# Identificação

- **Título do Projeto:** SoftMeter — Plataforma de Inspeção e Metrologia de Qualidade de Software
- **Linha de Projeto (Direction):** Web App
- **Autor:** [Seu Nome Completo]
- **Data da Proposta:** 12/04/2026
- **Versão:** 1.0

---

# 1. Visão do Produto e Impacto (O Problema)

> **Este projeto resolve um problema real ou é apenas um exercício técnico?**
>
> É um problema real, vivido diariamente por equipes de desenvolvimento e gestores de TI:
> softwares são entregues como "prontos" sem que existam critérios objetivos e quantitativos
> que comprovem essa afirmação.

---

## 1.1 Contexto e Problema

A indústria manufatureira opera há décadas sob um princípio inegociável: nenhuma peça é aceita sem medição. Tolerâncias dimensionais, laudos de inspeção e certificações metrológicas garantem que cada componente entregue atende precisamente ao que foi projetado. Um furo fora de centro por décimos de milímetro é motivo de rejeição imediata — não por subjetividade, mas porque existe um protocolo claro de medição e conformidade.

A Engenharia de Software, por sua vez, enfrenta um paradoxo persistente: **sistemas são entregues como "prontos" e "funcionando" sem que critérios objetivos de aceitação tenham sido rigorosamente definidos e medidos.** O que significa exatamente que um software é "rápido o suficiente"? Quantos erros de entrada de dados são toleráveis? Em que momento uma falha intermitente passa de "comportamento esperado" para "defeito crítico"?

Na ausência de métricas quantitativas claras, a qualidade de software torna-se uma percepção — e percepções variam entre clientes, desenvolvedores e gestores.

**Quem sofre com esse problema:**
- Gestores de TI que não conseguem provar objetivamente se o sistema entregue atende ao contrato
- Equipes de QA que realizam testes sem critérios numéricos de aceitação definidos
- Clientes que recebem software "funcionando" mas com desempenho aquém do esperado
- Desenvolvedores que não sabem quando parar de otimizar por falta de uma "tolerância" clara

**Como é resolvido hoje:**
- Testes informais baseados em percepção subjetiva do usuário
- Planilhas de acompanhamento sem cálculo automático de conformidade
- SLAs genéricos definidos em contrato mas nunca medidos sistematicamente
- Ferramentas de monitoramento que coletam dados mas não emitem "laudos de conformidade"

**Limitações das soluções atuais:**
- Ausência de um protocolo estruturado que ligue requisito → medição → desvio → laudo
- Ferramentas de QA focam em encontrar bugs, não em medir conformidade quantitativa
- Nenhuma ferramenta disponível traduz os conceitos maduros da metrologia industrial para o contexto de software

---

## 1.2 Origem da Demanda e Evidências

### Contexto Profissional do Autor

O projeto nasce da experiência profissional direta do autor como **técnico de metrologia dimensional** — operador de Braço de Medição FARO e software PolyWorks em ambiente de fabricação de peças de precisão — que, durante a transição de carreira para a Engenharia de Software, identificou a ausência de rigor metrológico nas práticas de QA das empresas que conheceu.

A observação central: **a mesma empresa que rejeitaria uma peça por 0,1 mm de desvio aceita um software com 40% dos requisitos não-funcionais fora do especificado**, simplesmente porque não existe um protocolo de inspeção equivalente.

### Evidência de Demanda no Mercado

Normas como a **ISO/IEC 25010** (SQuaRE — Systems and Software Quality Requirements and Evaluation) existem e definem características de qualidade de software com precisão. Contudo, a lacuna entre a existência dessas normas e sua **aplicação prática e automatizada** nas organizações permanece expressiva, especialmente em empresas de pequeno e médio porte.

A crítica de Sommerville (2011) — *"a ideia de tolerâncias não é aplicável aos sistemas digitais"* — evidencia exatamente o gap que este projeto se propõe a preencher: não há ferramentas que tornem essa aplicação prática e acessível.

### Evidência Técnica

Ferramentas existentes como SonarQube, New Relic e Grafana coletam métricas de código e performance, mas **nenhuma delas:**
- Permite definir um "valor nominal" com tolerâncias para cada requisito
- Calcula o "desvio" entre o medido e o esperado
- Emite um "Laudo de Conformidade" classificando o software como Conforme / Não-Conforme

---

## 1.3 Análise de Soluções Existentes (Benchmark)

### Soluções Investigadas

**1. SonarQube / SonarCloud**
- Link: https://www.sonarqube.org
- Público-alvo: Equipes de desenvolvimento
- Funcionalidades: Análise estática de código, detecção de bugs, code smells, cobertura de testes
- Limitações: Foca em qualidade de código-fonte, não em conformidade de requisitos não-funcionais em produção. Não emite laudos de conformidade.

**2. New Relic / Datadog**
- Link: https://newrelic.com / https://datadoghq.com
- Público-alvo: Times de DevOps e SRE
- Funcionalidades: Monitoramento de performance, alertas, dashboards
- Limitações: Focado em observabilidade operacional. Não permite definir tolerâncias por requisito nem gerar laudos comparativos entre versões.

**3. Jira + Xray (Test Management)**
- Link: https://www.atlassian.com/software/jira
- Público-alvo: Equipes de QA
- Funcionalidades: Gestão de casos de teste, execução, relatórios de cobertura
- Limitações: Focado em testes funcionais (pass/fail). Não quantifica desvios nem calcula índice de conformidade percentual.

**4. TestRail**
- Link: https://www.testrail.com
- Público-alvo: Gestores de QA
- Funcionalidades: Planejamento de testes, execução, relatórios
- Limitações: Mesma limitação do Jira/Xray — resultado binário, sem conceito de tolerância ou laudo metrológico.

### Comparação

| Solução | Pontos Fortes | Limitações |
|---|---|---|
| SonarQube | Análise de código profunda, integração CI/CD | Sem métricas de requisitos não-funcionais em produção |
| New Relic | Dados de performance em tempo real | Sem tolerâncias definíveis por requisito, sem laudo |
| Jira/Xray | Gestão de testes integrada ao desenvolvimento | Resultado binário, sem cálculo de desvio |
| TestRail | Relatórios de QA completos | Sem conformidade quantitativa metrológica |

### Diferencial do SoftMeter

O **SoftMeter** preenche uma lacuna específica não atendida por nenhuma das soluções acima:

1. **Define tolerâncias por requisito** — cada requisito tem um valor nominal, tolerância superior e inferior, assim como uma cota dimensional em metrologia
2. **Calcula desvios automaticamente** — a diferença entre o medido e o esperado é calculada e classificada
3. **Emite Laudos de Conformidade** — documento estruturado com índice percentual de conformidade e classificação (Conforme / Não-Conforme / Condicional)
4. **Rastreabilidade metrológica** — cada medição é vinculada a um ciclo de teste documentado, garantindo rastreabilidade

---

## 1.4 Público-Alvo

**Perfil primário — Analistas de QA / Testers**
- Profissionais responsáveis pela garantia de qualidade de sistemas
- Contexto: equipes de desenvolvimento de software em empresas de médio porte
- Nível técnico: intermediário — conhecem testes de software, não necessariamente metrologia

**Perfil secundário — Gestores de TI / Product Owners**
- Precisam provar para o cliente que o software entregue atende ao contratado
- Contexto: entrega de projetos para clientes externos
- Nível técnico: básico-intermediário — precisam de relatórios claros, não de dados técnicos brutos

**Perfil terciário — Desenvolvedores de software**
- Querem saber exatamente quando uma funcionalidade está "dentro da tolerância" antes do deploy
- Contexto: times ágeis com foco em qualidade contínua

---

## 1.5 Objetivos do Projeto

### Objetivo Geral

Desenvolver uma aplicação web — o **SoftMeter** — que implemente o framework de Metrologia de Software: um protocolo estruturado que transpõe os conceitos da metrologia industrial (tolerância, desvio, conformidade, laudo) para a Engenharia de Software, permitindo avaliar quantitativamente se um sistema de software atende aos seus requisitos especificados.

### Objetivos Específicos

1. **Mapear e transpor** os conceitos do Vocabulário Internacional de Metrologia (VIM) para equivalentes no domínio de software, fundamentando o framework teórico
2. **Implementar o cadastro de sistemas e requisitos** com definição de valores nominais e tolerâncias (superiores e inferiores) por requisito
3. **Implementar o registro de ciclos de teste e medições**, com cálculo automático de desvio absoluto, relativo e classificação de conformidade
4. **Gerar Laudos de Conformidade de Software** — documento com índice percentual de conformidade e classificação final (Conforme / Não-Conforme / Condicional)
5. **Aplicar o framework em um estudo de caso real**, validando a ferramenta com dados de um sistema conhecido pelo autor

---

## 1.6 Métricas de Sucesso (KPIs)

| KPI | Meta |
|---|---|
| Tempo de resposta da API | < 300ms para 95% das requisições |
| Disponibilidade do sistema | ≥ 99% (ambiente de staging/produção) |
| Cobertura de testes backend (TDD) | ≥ 75% |
| Cobertura de testes frontend | ≥ 25% |
| Tempo para gerar um laudo completo | < 5 segundos |
| Redução do tempo de documentação de QA | ≥ 50% vs processo manual em planilha (validado com usuário real) |

---

# 2. Engenharia de Requisitos

## 2.1 Personas

### Persona 1 — Ana Souza, Analista de QA

- **Idade:** 28 anos
- **Contexto:** Trabalha em uma softwarehouse de médio porte, responsável pelos testes de 3 produtos simultaneamente
- **Objetivos:** Ter critérios claros de aceitação para cada funcionalidade, documentar resultados de forma profissional
- **Dificuldades:** Testes baseados em "achismo", sem métricas definidas. Relatórios finais são subjetivos e contestados pelo cliente.

### Persona 2 — Carlos Mendes, Gerente de TI

- **Idade:** 42 anos
- **Contexto:** Gerencia a entrega de sistemas para prefeituras e órgãos públicos, que exigem laudos técnicos formais
- **Objetivos:** Ter documentação que prove que o software entregue atende ao contrato
- **Dificuldades:** Não existe nenhum "documento de conformidade" padronizado que os desenvolvedores emitam. Reclamações pós-entrega são frequentes.

### Persona 3 — Rafael Lima, Desenvolvedor Backend

- **Idade:** 25 anos, em início de carreira
- **Contexto:** Desenvolve APIs para um sistema de gestão e quer garantir qualidade antes do deploy
- **Objetivos:** Saber se sua API está "dentro da tolerância" de desempenho antes de subir para produção
- **Dificuldades:** Apenas testa se "funciona" — não tem base para dizer se está "bom o suficiente"

---

## 2.2 Casos de Uso Principais

1. Cadastrar sistema de software para avaliação
2. Definir requisitos com tolerâncias (cotas de software)
3. Registrar ciclo de teste (ambiente + versão)
4. Registrar medições por requisito
5. Visualizar desvios calculados automaticamente
6. Gerar e exportar Laudo de Conformidade
7. Comparar laudos entre versões do mesmo sistema

---

## 2.3 Requisitos Funcionais (RF)

**Gestão de Sistemas**
- RF01 — O sistema deve permitir que o usuário cadastre sistemas de software com nome, descrição e responsável.
- RF02 — O sistema deve permitir que o usuário liste, edite e arquive sistemas cadastrados.

**Gestão de Requisitos (Cotas)**
- RF03 — O sistema deve permitir que o usuário cadastre requisitos vinculados a um sistema, com: descrição, valor nominal, tolerância superior, tolerância inferior, unidade e criticidade.
- RF04 — O sistema deve permitir que o usuário classifique requisitos como Crítico, Maior ou Menor.
- RF05 — O sistema deve permitir que o usuário edite e desative requisitos sem perder o histórico de medições.

**Ciclos de Teste**
- RF06 — O sistema deve permitir que o usuário registre ciclos de teste vinculados a um sistema, com versão do software e descrição do ambiente.
- RF07 — O sistema deve permitir que o usuário encerre um ciclo de teste, bloqueando novas medições.

**Medições**
- RF08 — O sistema deve permitir que o usuário registre medições por requisito dentro de um ciclo, informando o valor medido e observações.
- RF09 — O sistema deve calcular automaticamente o desvio absoluto (medido − nominal) e o status de conformidade (Aprovado / Alerta / Reprovado).

**Laudos**
- RF10 — O sistema deve gerar automaticamente um Laudo de Conformidade ao encerrar um ciclo, com índice percentual de conformidade e classificação final.
- RF11 — O sistema deve permitir que o usuário visualize e exporte o laudo em PDF.
- RF12 — O sistema deve permitir que o usuário compare laudos de dois ciclos diferentes do mesmo sistema.

**Autenticação**
- RF13 — O sistema deve exigir autenticação para acesso a qualquer funcionalidade.
- RF14 — O sistema deve permitir que o usuário crie conta com e-mail e senha.

---

## 2.4 Requisitos Não Funcionais (RNF)

- RNF01 — O sistema deve responder a 95% das requisições de API em menos de 300ms.
- RNF02 — O sistema deve estar disponível em ambiente de produção via URL pública (cloud).
- RNF03 — O sistema deve utilizar autenticação com JWT e HTTPS.
- RNF04 — O sistema deve ter cobertura de testes unitários de no mínimo 75% no backend.
- RNF05 — O sistema deve ter pipeline CI/CD configurado via GitHub Actions.
- RNF06 — O sistema deve utilizar banco de dados PostgreSQL em produção.
- RNF07 — O sistema deve ser responsivo e utilizável em desktop e tablet.
- RNF08 — O sistema deve aplicar análise estática de código (SonarCloud ou CodeClimate).
- RNF09 — O sistema deve ter monitoramento básico de performance e disponibilidade.

---

## 2.5 Regras de Negócio

- RN01 — Um ciclo de teste encerrado não pode receber novas medições.
- RN02 — Um laudo só pode ser gerado se o ciclo tiver ao menos uma medição por requisito ativo.
- RN03 — O status "Alerta" é atribuído quando o valor medido está entre 95% e 100% do limite de tolerância.
- RN04 — O Índice de Conformidade Geral = (requisitos Aprovados / total de requisitos avaliados) × 100.
- RN05 — Classificação final: Conforme (≥ 90%), Condicional (70%–89%), Não-Conforme (< 70%).
- RN06 — Requisitos com criticidade "Crítico" reprovados resultam em classificação Não-Conforme independente do índice geral.

---

## 2.6 Fora do Escopo

- Integração automática com ferramentas de CI/CD para coletar medições (monitoramento passivo — o usuário insere os valores manualmente nesta versão)
- Testes de carga ou stress automatizados
- Suporte a múltiplos idiomas
- Aplicativo mobile nativo
- Gestão financeira ou contratual

---

# 3. Fluxos e Comportamento do Sistema

## 3.1 Fluxo Principal do Usuário

```
Login/Cadastro
     ↓
Dashboard (visão geral dos sistemas)
     ↓
Selecionar Sistema → Cadastrar Sistema
     ↓
Gerenciar Requisitos (definir cotas + tolerâncias)
     ↓
Abrir Ciclo de Teste (informar versão + ambiente)
     ↓
Registrar Medições (por requisito)
     ↓
Encerrar Ciclo
     ↓
Visualizar Laudo de Conformidade
     ↓
Exportar PDF / Comparar com versão anterior
```

## 3.2 Fluxos Alternativos

- **Requisito sem medição no ciclo:** sistema exibe alerta antes de encerrar o ciclo e impede geração do laudo.
- **Valor medido fora de tolerância crítica:** sistema exibe destaque visual em vermelho e força classificação Não-Conforme no laudo.
- **Tentativa de edição de ciclo encerrado:** sistema bloqueia e exibe mensagem explicativa.

---

# 4. Mockups e Experiência do Usuário (UX)

## 4.1 Fluxo de Navegação

```
/login → /dashboard → /sistemas → /sistemas/:id → /ciclos/:id → /laudos/:id
```

## 4.2 Telas Principais (Wireframes — a detalhar no próximo sprint)

**Tela 1 — Dashboard**
- Cards com sistemas cadastrados
- Indicadores: total de sistemas, ciclos abertos, laudos emitidos
- Ação principal: "+ Novo Sistema"

**Tela 2 — Detalhe do Sistema**
- Lista de requisitos com valor nominal e tolerâncias
- Lista de ciclos de teste com status
- Ação: "+ Novo Requisito" / "+ Novo Ciclo"

**Tela 3 — Ciclo de Teste (registro de medições)**
- Tabela com colunas: Requisito | Nominal | Tolerância | Valor Medido | Desvio | Status
- Campo de input para valor medido por linha
- Botão "Encerrar Ciclo e Gerar Laudo"

**Tela 4 — Laudo de Conformidade**
- Cabeçalho: sistema, versão, data, ambiente
- Tabela de medições completa com status colorido
- Índice de Conformidade Geral (% com barra de progresso)
- Classificação final em destaque (Conforme / Condicional / Não-Conforme)
- Botão "Exportar PDF"

---

# 5. Arquitetura do Sistema

## 5.1 Diagrama C4

### Nível 1 — Contexto

```
[Usuário (QA / Gestor / Dev)]
           |
    [SoftMeter Web App]
           |
    [PostgreSQL Database]
           |
    [Serviço de PDF (geração de laudos)]
```

Atores externos: usuário autenticado via browser.
Sistema principal: SoftMeter (backend API + frontend SPA).
Dependências externas: banco de dados relacional, geração de PDF.

### Nível 2 — Containers

```
Browser (React SPA)
    → REST API (Node.js / Express)
        → PostgreSQL (dados de sistemas, requisitos, medições, laudos)
        → PDF Generator (pdfkit ou puppeteer)
```

- **Frontend:** React + TypeScript, hospedado em CDN/cloud
- **Backend:** Node.js + Express + TypeScript
- **Banco:** PostgreSQL (produção), Docker local (desenvolvimento)
- **Auth:** JWT + bcrypt
- **CI/CD:** GitHub Actions → deploy automático

### Nível 3 — Componentes (Backend API)

```
routes/
  ├── auth.routes.ts       → AuthController
  ├── sistemas.routes.ts   → SistemasController → SistemasService → SistemasRepository
  ├── requisitos.routes.ts → RequisitosController → RequisitosService → RequisitosRepository
  ├── ciclos.routes.ts     → CiclosController → CiclosService → CiclosRepository
  ├── medicoes.routes.ts   → MedicoesController → MedicoesService (calcula desvios) → MedicoesRepository
  └── laudos.routes.ts     → LaudosController → LaudosService (gera PDF) → LaudosRepository
```

## 5.2 Modelo de Dados

```sql
-- Entidades principais
tb_usuarios (id, nome, email, senha_hash, created_at)
tb_sistemas (id, nome, descricao, responsavel, id_usuario, status, created_at)
tb_requisitos (id, id_sistema, codigo, descricao, valor_nominal, tolerancia_sup,
               tolerancia_inf, unidade, criticidade, ativo, created_at)
tb_ciclos_teste (id, id_sistema, versao_software, ambiente, status, data_inicio,
                 data_fim, created_at)
tb_medicoes (id, id_ciclo, id_requisito, valor_medido, desvio_absoluto,
             desvio_relativo, status_conformidade, observacao, created_at)
tb_laudos (id, id_ciclo, total_requisitos, total_aprovados, indice_conformidade,
           classificacao_final, pdf_url, created_at)
```

## 5.3 Principais Componentes

| Componente | Responsabilidade |
|---|---|
| Auth Service | Registro, login, geração e validação de JWT |
| Sistemas Service | CRUD de sistemas de software |
| Requisitos Service | CRUD de requisitos com tolerâncias |
| Ciclos Service | Abertura, gestão e encerramento de ciclos de teste |
| Medições Service | Registro de valores medidos e cálculo automático de desvios |
| Laudos Service | Geração do índice de conformidade e do PDF do laudo |

## 5.4 Stack Tecnológica

| Tecnologia | Justificativa |
|---|---|
| **Node.js + TypeScript** | Ecossistema rico, tipagem estática reduz bugs, vasta documentação |
| **Express.js** | Framework minimalista e flexível, adequado para APIs RESTful |
| **PostgreSQL** | Banco relacional robusto, preferido nas diretrizes do portfólio |
| **React + TypeScript** | Componentização, reatividade de estado, padrão de mercado |
| **Docker** | Garante ambiente de desenvolvimento consistente e portável |
| **GitHub Actions** | CI/CD nativo do GitHub, pipeline de testes e deploy automatizado |
| **Jest** | Framework de testes padrão para Node.js/React, suporte a TDD |
| **JWT + bcrypt** | Autenticação segura sem estado, padrão da indústria |

---

# 6. Segurança e Privacidade

## 6.1 Proteções Implementadas

- **Autenticação:** JWT com expiração configurável; tokens não armazenados em localStorage (uso de httpOnly cookies)
- **Senhas:** Hash com bcrypt (salt rounds ≥ 12)
- **HTTPS:** Obrigatório em produção via certificado SSL
- **Injeção SQL:** Uso de ORM/query builder com queries parametrizadas
- **CORS:** Configurado para aceitar apenas origens autorizadas
- **Variáveis sensíveis:** Secrets gerenciados via variáveis de ambiente (nunca no código-fonte)

## 6.2 Privacidade e LGPD

**Dados coletados:** nome, e-mail e senha do usuário; dados de sistemas e requisitos inseridos voluntariamente.

**Armazenamento:** banco de dados PostgreSQL com acesso restrito; senhas nunca armazenadas em texto claro.

**Remoção de dados:** o usuário pode solicitar exclusão da conta via interface, com remoção de todos os dados associados (Art. 18, LGPD).

**Não há coleta de dados sensíveis** (saúde, financeiros, biométricos) — o sistema processa dados técnicos de software, não dados pessoais de terceiros.

---

# 7. Planejamento do Projeto

| Marco | Descrição | Prazo |
|---|---|---|
| M1 — RFC aprovada | Documento de planejamento completo e revisado | Semana 2 |
| M2 — Setup + Estrutura | Repositório configurado, Docker, CI/CD básico, banco criado | Semana 3 |
| M3 — Backend MVP | CRUD de sistemas, requisitos e ciclos com autenticação | Semana 6 |
| M4 — Medições + Desvios | Registro de medições com cálculo automático de desvios | Semana 8 |
| M5 — Laudos | Geração do Laudo de Conformidade em PDF | Semana 10 |
| M6 — Frontend | Interface React funcional integrada ao backend | Semana 13 |
| M7 — Testes + CI/CD | Cobertura de testes ≥ 75%, pipeline completo, SonarCloud | Semana 15 |
| M8 — Deploy + Poster | Deploy em produção, poster técnico, Demo Day | Semana 18 |

---

# 8. Referências

- BASILI, V.R.; CALDIERA, G.; ROMBACH, H.D. **Goal Question Metric Paradigm**. Encyclopedia of Software Engineering, 1994.
- BUREAU INTERNATIONAL DES POIDS ET MESURES. **Vocabulário Internacional de Metrologia (VIM)**, 3ª ed. INMETRO, 2012.
- ISO/IEC 25010:2023. **Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — Product quality model**. ISO, 2023.
- SOMMERVILLE, Ian. **Engenharia de Software**, 9ª ed. Pearson, 2011.
- WINCK, Diogo Vinícius. **Mais Que Código: Um Manifesto para Projetos de Conclusão**. Medium, 2026. Disponível em: https://medium.com/@diogo.winck
- OWASP. **OWASP Top Ten**. Disponível em: https://owasp.org/www-project-top-ten/

---

# 9. Apêndices

## Apêndice A — Paralelo Metrologia Industrial × Software

| Metrologia Industrial | SoftMeter (Equivalente) |
|---|---|
| Desenho técnico / GD&T | Documento de Requisitos |
| Tolerância dimensional | Tolerância de requisito (sup/inf) |
| Medição com Braço FARO | Execução de testes e coleta de valores |
| Software PolyWorks | SoftMeter (análise e laudo) |
| Laudo de Inspeção | Laudo de Conformidade de Software |
| Peça aprovada / refugada | Software Conforme / Não-Conforme |
| Incerteza de medição | Variabilidade de performance entre ambientes |
| Calibração do instrumento | Padronização do ambiente de testes |

## Apêndice B — Exemplo de Laudo de Conformidade

| Característica | Nominal | Tolerância | Medido | Desvio | Status |
|---|---|---|---|---|---|
| Tempo de Login | 2,00 s | ± 0,50 s | 2,35 s | +0,35 s | ✔ Aprovado |
| Precisão de Cálculo (R$) | R$ 100,00 | R$ 0,00 | R$ 100,01 | +R$ 0,01 | ✘ Reprovado |
| Taxa de Erro de Input | 0% | Máx 2% | 1,5% | -0,5% | ✔ Aprovado |
| Disponibilidade | 99,9% | Mín 99,0% | 98,7% | -1,2% | ✘ Reprovado |

**Índice de Conformidade: 50% → Classificação: Não-Conforme**

---

# 10. Parecer do Comitê de Avaliação

*(A ser preenchido pelos professores)*

**Avaliador 1:** __________________________
**Status:** [ ] Aprovado [ ] Ajustar

Observações:

---

**Avaliador 2:** __________________________
**Status:** [ ] Aprovado [ ] Ajustar

Observações:

---

**Avaliador 3:** __________________________
**Status:** [ ] Aprovado [ ] Ajustar

Observações:
