# Guia de Contribuição — SoftMeter

Este documento orienta a colaboração via Pull Requests e Issues, conforme exigido pelo PAC
Extensionista (revisão por pares).

---

## Fluxo de trabalho

Toda mudança entra por **Pull Request para a `main`** — nunca por push direto. A `main` é
protegida: exige PR e os dois jobs de CI verdes (*Backend — Lint + Tipos + Testes* e *Frontend —
Lint + Tipos + Testes*), e a regra vale também para o dono do repositório (`enforce_admins`).

1. Crie uma branch a partir da `main` atualizada.
2. Faça as mudanças, com testes (unitário + integração + E2E para funcionalidade nova — Princípio II
   da constituição em `.specify/memory/constitution.md`).
3. Rode os testes localmente (ver [README](README.md#rodando-os-testes)).
4. Abra o PR, aguarde o CI e peça revisão.
5. Depois do merge, atualize a `main` local (`git pull --ff-only`).

Se houver mais de um PR aberto ao mesmo tempo, mescle um por vez: depois de cada merge os demais
ficam desatualizados em relação à `main` e precisam ser atualizados (e passar no CI de novo) antes
de mesclar.

## Branches

Nomes descritivos, com o tipo da mudança como prefixo:

- `feat/nome-da-feature` — novas funcionalidades
- `fix/nome-do-bug` — correções
- `docs/assunto` — documentação
- `chore/assunto` — manutenção sem mudança de comportamento
- `test/assunto` — somente testes

**Um assunto por PR.** Evite empacotar uma decisão de arquitetura (ADR) ou um fix paralelo em um
PR cujo título trata de outra coisa: depois fica difícil achar, por `git blame`/`git bisect`,
quando a decisão foi tomada.

## Padrão de commits (Conventional Commits)

```
feat: recuperação de senha via e-mail (Resend com fallback de log)
fix: seguir sem token quando o GITHUB_TOKEN é rejeitado pelo GitHub
test: implementar suíte E2E com Playwright
docs: revisar RFC-001 para v2.1
chore: ignorar documento de avaliação do orientador
refactor: extrair leitura de cobertura para serviço separado
```

## Descrição do Pull Request

Use o formato dos PRs recentes: **Resumo** (o que muda e por quê — inclusive como o problema foi
descoberto, quando for um bug) e **Test plan** (checklist do que foi rodado: `pytest`,
`ruff`/`mypy`, `tsc`/`eslint`, Jest, Playwright, validação manual).

## Como revisar o código de um colega (Code Review)

1. Acesse a aba **Pull requests** do repositório e abra o PR.
2. Leia o título e a descrição — entenda o que a mudança pretende resolver.
3. Navegue pelos arquivos em **Files changed** e leia o código, não só o resumo.
4. Comente nas linhas relevantes. Uma boa revisão **aponta um problema, sugere uma mudança ou
   questiona uma decisão**, explicando o motivo e o impacto (ex.: um side-channel de timing, um
   endpoint fora do rate limit, uma suposição de ambiente que não vale em produção).
   "Ok", "ficou bom" e "aprovado" sozinhos não são revisão.
5. Finalize com **Approve**, **Comment** ou **Request changes**.

Quem recebe a revisão responde cada comentário: corrige no próprio PR (ou em um PR de
acompanhamento, citando o comentário original) ou explica por que mantém a decisão.

## Decisões de arquitetura (ADR)

Mudanças de stack, de integração externa ou de modelo de dados são registradas como ADR em
[`docs/adr/`](docs/adr/) (numeração sequencial). ADRs não são reescritos: quando uma decisão é
superada, o novo ADR a referencia e o antigo recebe uma nota.

## Como reportar um bug (Issue)

```
**Título:** [BUG] Descrição curta

**Passos para reproduzir:**
1. ...

**Esperado:** ...
**Atual:** ...
**Ambiente:** (OS, navegador, versão do Docker; Python/Node se rodar fora do container)
**Logs:** (saída do backend/worker, sem tokens ou senhas)
```

## Segredos

Nunca versione `.env`, tokens ou chaves (use o [`.env.example`](.env.example) como modelo). Se um
segredo for commitado por engano, considere-o comprometido: revogue e gere outro.
