# ADR-011: Escopo dos Arquivos Analisados e Escolha da Cobertura

**Data:** 08/11/2026
**Status:** Aceito
**Autor:** Diego Cunha
**Origem:** revisão por pares do Sandro Machiniski — issue #100

---

## Contexto

As métricas eram calculadas sobre arquivos que **não são código autoral de produção**, e a cobertura lia um
arquivo escolhido sem critério:

- `IGNORED_DIR_NAMES` não cobria `.next`, `.nuxt`, `out`, `target`, `env`, `site-packages`,
  `bower_components` nem `migrations`; `*.min.js` e `*.d.ts` não eram filtrados. Um bundle minificado vira
  uma única "função" gigante e distorce a média do repositório inteiro.
- `coverage_reader` usava `rglob("coverage.xml")[0]` **sem** ignorar diretórios de terceiros (podia ler o de
  `node_modules` ou `venv`) e, em monorepos com mais de um relatório, o escolhido dependia da ordem do
  sistema de arquivos — a cobertura do laudo não era reprodutível.
- Arquivos de teste entravam nas médias como se fossem produção. Depois da correção do acoplamento
  (ADR-010) isso ficou visível: no `pallets/click`, os módulos de teste (que só importam) elevavam a
  instabilidade média de 0,66 para 0,86 e viravam o laudo de Conforme para Não-Conforme.

## Decisão

- **Arquivos gerados/de terceiros ficam de fora:** novos diretórios ignorados (lista acima), `*.min.*`,
  `*.d.ts`, `*.bundle.js` e uma heurística de minificado (arquivo ≥ 2 KB com média de linha > 200
  caracteres, mesmo sem o sufixo `.min.`).
- **Testes ficam de fora de CC, LOC, MI, acoplamento e duplicação** (decisão de produto, a documentar no
  catálogo): diretórios `test`/`tests`/`__tests__`/`spec`/`specs`/`e2e`/`__mocks__` e arquivos
  `test_*.py`, `*_test.py`, `conftest.py`, `*.test.*`, `*.spec.*`. O SoftMeter mede o código de produção;
  testes repetem estrutura por natureza e, no grafo de imports, só importam. A **Cobertura de Testes**
  continua sendo lida normalmente.
- **Cobertura determinística:** a busca de `coverage.xml`/`lcov.info` ignora diretórios de dependências e
  ambientes (lista própria — não a das métricas, porque `coverage/` é onde o `lcov.info` costuma ficar) e
  ordena por **caminho mais raso primeiro, depois alfabético**. Com mais de um relatório que informe
  total de linhas, eles são **combinados por soma de linhas** (média ponderada); se algum não informar,
  vale o primeiro.
- **Erro claro sem código analisável:** se nada restar depois das exclusões, a análise falha com
  "Nenhum código analisável: …" em vez de uma exceção obscura de métrica ausente; o repositório **não** é
  marcado como inacessível.

## Consequências

- **Os valores mudam de novo.** Medido (antes → depois deste ADR): `pallets/click` — acoplamento 0,86 →
  0,66, duplicação 21,2% → 10,3%, LOC 6,9 → 14,5, laudo Não-Conforme → Conforme; `psf/requests` —
  duplicação 15,1% → 6,1%, laudo Condicional → Conforme. O LOC sobe porque os testes tinham muitas funções
  minúsculas. Análises já gravadas não são recalculadas.
- **Repositório só com testes** deixa de ser analisável (falha com mensagem clara).
- **`pypa/sampleproject`** passa a mostrar Acoplamento "Não disponível": seus dois módulos de produção não
  importam um ao outro, e sem nenhuma aresta resolvida não dá para distinguir isso de "não consegui resolver"
  (ADR-010). É o preço de nunca mais mostrar um falso "Conforme".
- **Limitação conhecida:** os *artifacts* de CI continuam sendo lidos um por vez (o mais recente com
  "coverage" no nome); só os relatórios versionados no código são combinados. Em monorepo com vários
  artifacts de cobertura, a escolha ainda depende do que o CI publicou por último.
- Aliases de `tsconfig` via `extends` e a convenção de nome de testes de outras linguagens ficam fora.
