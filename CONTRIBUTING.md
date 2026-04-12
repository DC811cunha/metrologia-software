# Guia de Contribuição — SoftMeter

Este documento orienta a colaboração via Pull Requests e Issues,
conforme exigido pelo PAC Extensionista (revisão por pares).

---

## Como revisar o código de um colega (Code Review)

1. Acesse a aba **Pull Requests** do repositório
2. Leia o título e a descrição do PR
3. Navegue pelos arquivos alterados em **Files changed**
4. Deixe comentários nas linhas relevantes
5. Finalize com **Approve**, **Comment** ou **Request changes**

## Como reportar um bug (Issue)

```
**Título:** [BUG] Descrição curta

**Passos para reproduzir:**
1. ...

**Esperado:** ...
**Atual:** ...
**Ambiente:** (OS, browser, Node version)
```

## Padrão de commits (Conventional Commits)

```
feat: adiciona cálculo de desvio relativo
fix: corrige classificação de crítico reprovado
test: adiciona testes para índice de conformidade
docs: atualiza RFC com requisitos funcionais
refactor: extrai lógica de laudo para serviço separado
```

## Branches

- `main` — produção, protegida
- `develop` — integração, todos os PRs vão para cá
- `feat/nome-feature` — novas funcionalidades
- `fix/nome-bug` — correções
