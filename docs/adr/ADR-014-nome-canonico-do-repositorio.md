# ADR-014: Nome Canônico do Repositório e Detecção de Troca de Dono do Nome

**Data:** 13/11/2026
**Status:** Aceito
**Autor:** Diego Cunha
**Origem:** caso real — `SandroMachiniski-SE/Viaje-Mais` foi renomeado para `NomadPlan`

---

## Contexto

Quando um repositório é renomeado ou transferido, o GitHub mantém um redirecionamento (301) do nome antigo
para o novo, e o SoftMeter passou a segui-lo. Isso mantinha a **análise** funcionando, mas o cadastro seguia
com o nome antigo: a lista e o relatório PDF exibiam o nome desatualizado, e cadastrar a mesma URL com os dois
nomes criava dois repositórios. Pior: se alguém criar **outro** repositório com o nome antigo, o GitHub desfaz
o redirecionamento e o cadastro antigo passaria a medir o repositório errado, sem nenhum aviso.

## Decisão

- Cada análise já consulta `/repos/{dono}/{nome}`; essa resposta (já com o redirecionamento resolvido) traz o
  `full_name` atual e o `id` numérico. O `GithubService` guarda essa **identidade observada** em
  `repo_identity`, sem nenhuma chamada extra à API.
- Nova coluna `repositories.github_id` (id numérico, que nunca muda). Preenchida na primeira análise.
- **Renomeação:** se o nome atual difere do cadastrado, `url` e `owner_nome` são atualizados para o canônico
  (inclusive só de maiúsculas/minúsculas). As análises e relatórios passam a usar o nome novo.
- **Nome reutilizado:** se o `github_id` gravado difere do observado, o nome cadastrado agora aponta para
  **outro** repositório: a análise é barrada (`409`, registrada como falha) com a orientação de remover e
  cadastrar de novo. Nada é medido nem baixado.
- **Duplicata:** se a mesma conta já tem outro cadastro com a URL canônica, o cadastro **não é renomeado**
  (a restrição de unicidade impediria) e a análise segue normalmente. Os históricos **não são fundidos**
  automaticamente: fundir apaga/mistura dados e fica a critério do usuário.

## Consequências

- A atualização acontece na **primeira análise depois da renomeação**, não no instante em que ela ocorre
  no GitHub (o SoftMeter não é notificado).
- Cadastros anteriores a esta mudança têm `github_id` nulo até a primeira análise; se o nome já tiver sido
  reutilizado antes disso, não há como detectar (só se detecta a partir do primeiro id gravado).
- No cadastro, a URL ainda é gravada como foi digitada; cadastrar o nome antigo de um repositório que já foi
  renomeado e atualizado cria um segundo cadastro até a primeira análise dele. Resolver isso exigiria uma
  chamada extra ao GitHub durante o cadastro.
- Exige a migration `add github_id to repositories` (`alembic upgrade head`).
