# ADR-001: Escolha da Stack Tecnológica

**Data:** 12/04/2026
**Status:** Aceito
**Autor:** [Seu Nome]

---

## Contexto

O SoftMeter é uma aplicação web com backend API, banco de dados relacional e frontend SPA.
As diretrizes do Portfólio da Católica SC recomendam o uso de linguagens e stacks modernas
com amplo suporte e comunidade ativa.

## Decisão

Adotar a seguinte stack:

| Camada | Tecnologia | Versão |
|---|---|---|
| Runtime | Node.js | 20 LTS |
| Linguagem | TypeScript | 5.x |
| Framework API | Express.js | 4.x |
| Banco de dados | PostgreSQL | 16 |
| Frontend framework | React | 18 |
| Testes | Jest + Testing Library | 29.x |
| Containerização | Docker + Docker Compose | 25.x |
| CI/CD | GitHub Actions | — |

## Justificativa

- **Node.js + TypeScript:** Preferido nas diretrizes do portfólio, tipagem estática reduz
  erros em tempo de desenvolvimento, grande ecossistema de bibliotecas para APIs REST.
- **PostgreSQL:** Explicitamente listado como "preferir" nas diretrizes do portfólio.
  Suporte robusto a transações, índices e queries complexas necessárias para cálculos
  de conformidade metrológica.
- **React:** Padrão de mercado para SPAs, vasta documentação, suporte ao TypeScript nativo.
- **Jest:** Framework de testes padrão para o ecossistema Node.js/React, indispensável
  para TDD obrigatório nas diretrizes do portfólio (≥75% backend).
- **Docker:** Listado como "preferir" nas diretrizes; garante ambiente consistente entre
  desenvolvimento e produção.

## Consequências

- Necessário conhecimento de TypeScript para contribuição ao projeto
- Deploy requer ambiente com suporte a Docker ou Node.js 20+ e PostgreSQL
- Cobertura de testes obrigatória ≥ 75% no backend monitorada via CI/CD
