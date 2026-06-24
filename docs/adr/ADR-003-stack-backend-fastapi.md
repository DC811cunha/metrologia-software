# ADR-003: Pivô do Backend para FastAPI/Python e Motor de Análise Assíncrono

**Data:** 24/06/2026
**Status:** Aceito
**Autor:** Diego Cunha

---

## Contexto

O ADR-001 estabeleceu Node.js + TypeScript + Express como stack de backend, por ser
**recomendada** (não obrigatória) nas diretrizes do Portfólio da Católica SC, e por isso foi
adotada como stack vinculante na constituição do projeto (v1.0.0).

Ao planejar a implementação da feature `001-softmeter-plataforma-mvp` (cadastro de
repositórios, execução de análise automática, dashboard de gauges metrológicos, histórico,
relatórios PDF e autenticação), o motor de análise de métricas precisa:

- Calcular Complexidade Ciclomática, LOC e Índice de Manutenibilidade a partir de código-fonte
  Python e JavaScript/TypeScript;
- Executar análises potencialmente custosas sem bloquear a requisição HTTP, respeitando o
  limite de 10 segundos do Princípio IV da constituição (ou degradando para processamento
  assíncrono quando o repositório for maior);
- Gerar relatórios PDF técnicos com fórmulas, fontes bibliográficas e limites de especificação
  (Princípio V).

O ecossistema Python oferece bibliotecas de análise estática maduras para esse domínio (Radon
para complexidade/MI/LOC), o que reduziria significativamente o esforço de implementar um
parser AST próprio do zero quando comparado a escrever todo o motor de análise em
TypeScript/Node.

## Decisão

Adotar a seguinte stack revisada, substituindo o backend Node.js/Express definido no ADR-001:

| Camada | Tecnologia | Versão |
|---|---|---|
| Backend / API | FastAPI | — |
| Linguagem (backend) | Python | 3.12 |
| Banco de dados | PostgreSQL | 16 |
| Processamento assíncrono | Celery + Redis | — |
| Cálculo de métricas | Radon + parser AST próprio (acoplamento, duplicação) | — |
| Frontend framework | React + TypeScript | 18 |
| Build tool (frontend) | Vite | — |
| Visualização/gráficos | Recharts | — |
| Geração de relatórios PDF | ReportLab (backend) | — |
| Autenticação | JWT (access + refresh token) + bcrypt | — |
| Containerização | Docker + Docker Compose | — |
| CI/CD | GitHub Actions | — |

O backend Node.js + TypeScript + Express criado sob o ADR-001 (`src/backend/`) é **descontinuado**
e será substituído pelo novo serviço FastAPI no mesmo caminho lógico (`src/backend/`), conforme
detalhado no plano de implementação da feature `001-softmeter-plataforma-mvp`.

## Justificativa

- **FastAPI + Python 3.12**: ecossistema com bibliotecas de análise estática de código maduras
  (Radon) reduz o esforço de implementação do motor de medição, que é o núcleo de valor do
  projeto. FastAPI é assíncrono nativamente, o que se integra bem com filas de processamento em
  segundo plano.
- **Celery + Redis**: necessário para cumprir o Princípio IV (Performance da Análise <10s) com
  degradação graciosa — análises maiores são despachadas para uma fila em vez de bloquear a
  requisição HTTP.
- **Radon + parser AST próprio**: Radon cobre Complexidade Ciclomática, LOC e Índice de
  Manutenibilidade com fórmulas publicadas e rastreáveis (Princípio V); Acoplamento e Score de
  Duplicação não têm uma biblioteca padrão única para os dois idiomas suportados, exigindo um
  parser AST próprio (via módulo `ast` do Python e um parser equivalente para JS/TS).
- **React 18 + TypeScript + Vite**: mantém a escolha de frontend do ADR-001 (React+TS), apenas
  trocando o bundler (Vite no lugar de Create React App/outro), sem impacto na constituição.
- **Recharts**: biblioteca de gráficos React madura, suficiente para os gauges metrológicos e
  para a visualização de tendências do histórico de análises.
- **ReportLab**: geração de PDF nativa em Python, evitando dependência de serviços externos de
  renderização de PDF.
- **JWT + refresh token + bcrypt**: padrão de mercado para autenticação stateless em APIs REST,
  compatível com FastAPI.

## Consequências

- O backend Node.js + TypeScript + Express implementado sob o ADR-001 é descontinuado; qualquer
  código já escrito nele precisa ser portado ou reescrito em Python/FastAPI.
- A equipe (autor do TCC) passa a manter duas linguagens no projeto: Python no backend e
  TypeScript no frontend, em vez de TypeScript em ambas as camadas.
- A cobertura de testes mínima de 80% (Princípio I da constituição) passa a ser medida com
  `pytest-cov` no backend (em vez de Jest), mantendo Jest apenas no frontend.
- Esta decisão diverge da recomendação (não obrigatoriedade) de Node.js nas diretrizes do
  Portfólio da Católica SC; a divergência é justificada pela maturidade do ecossistema Python
  para análise estática de código, núcleo de valor do produto.
- A constituição do projeto é emendada (v1.0.0 → v2.0.0) para refletir esta nova stack vinculante.
