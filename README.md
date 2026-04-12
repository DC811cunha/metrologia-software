# SoftMeter 📐

> **Metrologia de Software** — Plataforma de Inspeção e Conformidade de Qualidade de Software

[![CI](https://github.com/SEU_USUARIO/metrologia-software/actions/workflows/ci.yml/badge.svg)](https://github.com/SEU_USUARIO/metrologia-software/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🎯 O Problema

Softwares são entregues como "prontos" sem que existam critérios objetivos e quantitativos
que comprovem essa afirmação. Na indústria manufatureira, nenhuma peça é aceita sem
medição — existem tolerâncias, laudos de inspeção e protocolos de conformidade.

**Por que o software não tem o mesmo rigor?**

O SoftMeter traz o protocolo da metrologia industrial para a Engenharia de Software:
cada requisito recebe um **valor nominal** e **tolerâncias** (assim como uma cota dimensional),
cada ciclo de testes gera **medições com desvios calculados automaticamente** e cada entrega
resulta em um **Laudo de Conformidade de Software** — Conforme, Condicional ou Não-Conforme.

---

## 🗂️ Estrutura do Repositório

```
metrologia-software/
├── docs/
│   ├── rfc/                        # Documento RFC do projeto
│   │   └── RFC-001-metrologia-software.md
│   ├── architecture/               # Diagramas C4 e decisões de arquitetura
│   └── adr/                        # Architecture Decision Records
├── src/
│   ├── backend/                    # API Node.js + TypeScript + Express
│   │   ├── src/
│   │   │   ├── controllers/        # Camada de entrada HTTP
│   │   │   ├── services/           # Regras de negócio
│   │   │   ├── repositories/       # Acesso ao banco de dados
│   │   │   ├── models/             # Tipagens e interfaces
│   │   │   ├── routes/             # Definição de rotas
│   │   │   └── middleware/         # Auth, validação, erros
│   │   ├── tests/                  # Testes unitários e integração (Jest)
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── Dockerfile
│   └── frontend/                   # SPA React + TypeScript
│       ├── src/
│       │   ├── components/         # Componentes reutilizáveis
│       │   ├── pages/              # Telas da aplicação
│       │   └── services/           # Chamadas à API
│       ├── tests/                  # Testes de componentes
│       ├── package.json
│       └── Dockerfile
├── scripts/                        # Scripts de setup e migrations
├── .github/
│   └── workflows/
│       └── ci.yml                  # Pipeline CI/CD (GitHub Actions)
├── docker-compose.yml              # Ambiente local completo
├── .env.example                    # Variáveis de ambiente necessárias
└── README.md
```

---

## 🚀 Como rodar localmente

### Pré-requisitos

- [Docker](https://www.docker.com/) e Docker Compose
- [Node.js](https://nodejs.org/) v20+
- [Git](https://git-scm.com/)

### Setup em 3 passos

```bash
# 1. Clone o repositório
git clone https://github.com/SEU_USUARIO/metrologia-software.git
cd metrologia-software

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas configurações locais

# 3. Suba o ambiente completo
docker-compose up --build
```

A aplicação estará disponível em:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:3001
- **Banco de dados:** localhost:5432

### Rodando os testes

```bash
# Backend
cd src/backend
npm install
npm test

# Frontend
cd src/frontend
npm install
npm test
```

---

## 🏗️ Stack Tecnológica

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Backend | Node.js + TypeScript + Express | Ecossistema rico, tipagem estática, alto desempenho |
| Frontend | React + TypeScript | Componentização, padrão de mercado |
| Banco de dados | PostgreSQL | Robusto, relacional, suportado nas diretrizes do portfólio |
| Testes | Jest + Testing Library | Padrão TDD para Node.js e React |
| Container | Docker + Docker Compose | Ambiente consistente e portável |
| CI/CD | GitHub Actions | Integrado ao repositório, automação de testes e deploy |
| Qualidade de código | SonarCloud (a configurar) | Análise estática e cobertura de testes |
| Monitoramento | New Relic / Grafana (a configurar) | Observabilidade em produção |

---

## 📐 O Framework Metrológico

### Analogia Metrologia Industrial × Software

| Metrologia Industrial | SoftMeter |
|---|---|
| Desenho técnico / GD&T | Documento de Requisitos |
| Tolerância dimensional | Tolerância por requisito (sup/inf) |
| Medição com Braço FARO | Coleta de valores em ciclo de testes |
| Software PolyWorks | SoftMeter |
| Laudo de Inspeção | Laudo de Conformidade de Software |
| Peça aprovada / refugada | Software Conforme / Não-Conforme |

### Classificação do Laudo

| Índice de Conformidade | Classificação |
|---|---|
| ≥ 90% | ✅ Conforme |
| 70% – 89% | ⚠️ Condicional |
| < 70% | ❌ Não-Conforme |

> **Obs.:** Qualquer requisito com criticidade **Crítica** reprovado resulta em Não-Conforme independente do índice geral.

---

## 📋 Documentação

- 📄 [RFC-001 — Documento de Proposta do Projeto](docs/rfc/RFC-001-metrologia-software.md)
- 🏛️ [Decisões de Arquitetura (ADR)](docs/adr/)
- 🖼️ [Diagramas C4](docs/architecture/)

---

## 📚 Referências Acadêmicas

- BASILI, V.R. et al. **Goal Question Metric Paradigm** (1994)
- VIM — **Vocabulário Internacional de Metrologia**, INMETRO (2012)
- ISO/IEC 25010:2023 — **SQuaRE — Product Quality Model**
- SOMMERVILLE, Ian. **Engenharia de Software**, 9ª ed. (2011)
- WINCK, D.V. **Mais Que Código**, Medium (2026)

---

## 🎓 Contexto Acadêmico

Este projeto é o Trabalho de Conclusão de Curso (Portfólio) do curso de **Engenharia de Software**
da **Católica SC**, desenvolvido segundo as diretrizes do [Portfolio Playbook](https://github.com/CatolicaSC-Portfolio/The-Portfolio-Playbook).

**Disciplinas envolvidas:**
- PAC Extensionista VII (RFC e planejamento)
- PAC Extensionista VIII (validação e QA por pares)
- Portfólio (desenvolvimento e entrega — Poster + Demo Day)

---

## 📝 Licença

Este projeto está licenciado sob a [MIT License](LICENSE).
