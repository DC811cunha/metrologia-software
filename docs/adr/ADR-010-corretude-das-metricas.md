# ADR-010: Corretude das Métricas — Acoplamento, Duplicação e LOC

**Data:** 08/11/2026
**Status:** Aceito
**Autor:** Diego Cunha
**Origem:** revisão por pares do Sandro Machiniski — issues #92, #93 e #94 (todas reproduzidas antes de corrigir)

---

## Contexto

Três métricas podiam dar um valor **errado sem avisar**, o que num projeto de metrologia é o pior defeito:

- **#92 Acoplamento:** os imports Python eram resolvidos pelo nome pontuado a partir da *raiz do repositório*
  (`src.backend.app.core.config`), mas o código importa `app.core.config`; em layouts `src/` ou
  `backend/app/` nenhum import era resolvido. Sem arestas, a função devolvia `0.0` ("Conforme"). Em
  TypeScript só imports relativos entravam no grafo; aliases (`@/componentes/X`) viravam "pacote externo".
- **#93 Duplicação:** `import os` e `import sys` viram a mesma linha normalizada, e janelas de 6 linhas do
  mesmo arquivo podiam se sobrepor e "casar" umas com as outras. Resultado reproduzido: 12 imports
  distintos → 100% de duplicação; um `Enum` de 12 membros → 85,7%.
- **#94 LOC:** em JS/TS, linhas internas de um comentário de bloco contavam como código, e uma linha como
  `/* nota */ return x;` era descartada inteira. Reproduzido: `f` = 5 (esperado 3), `g` = 2 (esperado 3).
  Além disso o Python alimentava o Índice de Manutenibilidade com `lloc` (linhas lógicas) e o JS/TS com
  linhas físicas, contrariando o catálogo (SLOC) e o Princípio V (consistência entre linguagens).

## Decisão

**Acoplamento**
- Python: o nome do import é casado com o **sufixo do caminho** dos módulos (qualquer layout). Se mais de
  um módulo casar, o import é ignorado: melhor sem aresta que com aresta errada. Um nome de um segmento só
  casa com pacotes (`__init__.py`), para `import config` não virar aresta falsa.
- JS/TS: lê `paths`/`baseUrl` do `tsconfig.json`/`jsconfig.json` **mais próximo** (aceita comentários e
  vírgulas finais). `extends` não é seguido.
- Em repositório com mais de um módulo e **nenhum** import interno resolvido, o valor é `None`
  ("Não disponível", agora permitido para o acoplamento) em vez de `0.0`.

**Duplicação**
- Linhas de `import`/`from … import`/`export … from`/`require()` não entram.
- Uma janela precisa ter ao menos **4 linhas normalizadas distintas** (descarta membros de Enum, campos de
  dataclass e sequências de asserts) e janelas do **mesmo arquivo** não casam se estiverem sobrepostas.
- Arquivo com apenas imports/comentários rende **0%** (não `None`, que a métrica não permite).

**LOC / Manutenibilidade**
- LOC de JS/TS e o SLOC do arquivo usam os nós `comment` do **tree-sitter**: conta linhas físicas com ao
  menos um token que não seja comentário. O Python passa a usar `sloc` (e não `lloc`) na fórmula do MI.

## Consequências

- **Os valores mudam.** Medido em repositórios reais: duplicação do `pallets/click` 28,2% → 21,2% e do
  `psf/requests` 23,9% → 15,1% (imports deixaram de contar); MI do `click` 63,3 → 61,1 (SLOC no lugar de
  `lloc`); acoplamento do `pypa/sampleproject` 0,0 → 0,5 (o `0,0` era um falso "Conforme"). Análises já
  gravadas **não** são recalculadas: o histórico de um repositório pode mostrar um degrau entre a
  análise antiga e a nova.
- Em repositórios sem imports internos detectáveis (scripts independentes) o acoplamento fica "Não
  disponível" e sai do resultado geral, como a cobertura.
- O acoplamento agora conta os módulos de teste, que são instáveis por natureza (só importam); o escopo dos
  arquivos analisados é tratado junto da issue #100.
