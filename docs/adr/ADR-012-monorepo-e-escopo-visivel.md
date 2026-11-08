# ADR-012: Suporte a Monorepo e Escopo da Medição Visível

**Data:** 08/11/2026
**Status:** Aceito
**Autor:** Diego Cunha
**Origem:** pendências deixadas no ADR-011 (issue #100 e discussão com o autor da revisão)

---

## Contexto

O ADR-011 tirou os testes das métricas de código e deixou três pontos em aberto:

1. A decisão só existia na documentação: quem olhava o dashboard ou o PDF não via que testes, dependências
   e arquivos gerados ficam de fora, e podia concluir que o SoftMeter errava a contagem.
2. Em monorepos o CI costuma publicar **um artifact de cobertura por parte** (`backend-coverage`,
   `frontend-coverage`) no mesmo run. O SoftMeter lia só o primeiro, então a cobertura dependia de qual
   parte tinha terminado de subir por último. É o caso do próprio SoftMeter.
3. O alias de import de projetos TypeScript que usam `extends` (ex.: `tsconfig.base.json`) não era
   resolvido, e o acoplamento podia cair para "Não disponível".

## Decisão

**Escopo visível.** O dashboard mostra, acima dos medidores, que arquivos de teste, dependências e
arquivos gerados ou minificados não entram nas métricas de código e que a cobertura vem dos relatórios do
repositório. O relatório PDF (análise única e histórico) traz a mesma nota. O texto vive em
`SCOPE_NOTE` (backend, usado no PDF) e `SCOPE_NOTE` (frontend, usado no dashboard), que devem acompanhar um ao outro.

**Cobertura de monorepo.** São baixados **todos os artifacts de cobertura do run de CI mais recente**
(até `MAX_COVERAGE_ARTIFACTS`, padrão 5; cada um respeitando o teto de tamanho). Dentro de cada artifact
vale `coverage.xml` antes de `lcov.info` (os dois descrevem as mesmas linhas; somá-los contaria tudo em
dobro) e, entre artifacts, os relatórios são **combinados por soma de linhas cobertas e totais**. Um artifact
corrompido ou grande demais é pulado sem descartar os demais; sem informação de run, vale só o mais novo.

**`extends` do tsconfig.** O `extends` é seguido por caminho relativo (com `.json` implícito, lista do
TypeScript 5, profundidade máxima de 5 e proteção contra ciclos). O arquivo filho sobrescreve o pai chave a
chave; `paths` é relativo ao `baseUrl` efetivo ou, sem ele, ao tsconfig que o definiu. Pacotes npm
(`@tsconfig/...`) são ignorados por não estarem no código analisado.

## Consequências

- Cada análise com token faz até `1 + MAX_COVERAGE_ARTIFACTS` chamadas à API do GitHub para a cobertura
  (antes, 2). Com o token do `.env` (5000 requisições/hora) isso é irrelevante; sem token a fonte já era pulada.
- Em medição real do SoftMeter: `frontend-coverage` (lcov) 91,2% e `backend-coverage` (xml) 92,5% passam a
  render **92,2%** combinados, em vez de um dos dois conforme a ordem de upload.
- Artifacts de *runs diferentes* (por exemplo, o backend publicado só em um workflow e o frontend em outro)
  não são combinados: vale o run mais recente que tenha artifact de cobertura.
- O texto de escopo existe em dois lugares (backend e frontend); uma mudança de critério exige atualizar os dois.
