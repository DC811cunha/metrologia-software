# ADR-009: Limites de Custo ao Baixar e Analisar Repositórios de Terceiros

**Data:** 08/11/2026
**Status:** Aceito
**Autor:** Diego Cunha
**Origem:** revisão por pares do Sandro Machiniski — issue #99

---

## Contexto

O SoftMeter baixa e processa conteúdo controlado por terceiros (qualquer repositório público do
GitHub), e nada limitava o custo disso:

1. `download_and_extract` carregava o zipball inteiro em memória e extraía tudo. O campo `size` da API
   do GitHub mede o repositório **compactado pelo git**; um repositório pequeno pode ter conteúdo
   descompactado enorme (dados, binários, arquivos repetitivos) e encher o disco ou a memória do worker.
2. `size_kb` só escolhia entre análise síncrona e assíncrona — nunca recusava um repositório grande.
3. A análise síncrona roda **dentro da requisição HTTP** sem prazo, ocupando uma thread do servidor.
4. O artifact de cobertura de CI era baixado e lido sem teto, e o `coverage.xml` de terceiros era lido
   com o parser XML padrão, vulnerável à expansão de entidades ("billion laughs").
5. Os arquivos eram percorridos por funções recursivas, e um arquivo com aninhamento extremo estourava o
   limite de recursão do Python, falhando a análise inteira.

## Decisão

Todos os tetos são configuráveis (`MAX_*`, `ANALYSIS_TIME_LIMIT_S`):

| Limite | Padrão | Onde atua |
|---|---|---|
| Tamanho do repositório segundo o GitHub | 200 MB | `POST /analyses` recusa com **422** e registra a análise como falha |
| Tamanho do download (zipball) | 100 MB | streaming para arquivo temporário; aborta ao passar do teto |
| Tamanho descompactado | 400 MB | soma dos `file_size` do ZIP, conferida **antes** de extrair |
| Número de arquivos | 30.000 | idem |
| Tamanho de arquivo-fonte analisado | 1 MB | arquivos maiores (gerados/minificados/dados) são ignorados |
| Artifact/arquivo de cobertura | 20 MB | baixar/ler acima disso é ignorado ("Não disponível") |
| Tempo de análise | 300 s | prazo **cooperativo** (laços por arquivo) + `soft_time_limit`/`time_limit` no Celery |

Além disso: o XML de cobertura passa a ser lido com `defusedxml`; `walk_tree` virou iterativo; e um arquivo
com recursão excessiva é **ignorado**, sem derrubar a análise. Estouros de tamanho viram
`RepositoryTooLargeError`: a análise é gravada como `falhou` com o motivo, **sem** marcar o repositório
como inacessível (ele existe, só é grande demais).

## Justificativa

- **Streaming para arquivo temporário** (`SpooledTemporaryFile`) mantém a memória constante e permite
  abortar no meio, em vez de baixar tudo para só então medir.
- **Prazo cooperativo no caminho síncrono:** uma thread de requisição não pode ser morta de fora; os
  laços por arquivo verificam o prazo e a própria análise se aborta. O Celery cobre o caso do worker
  por cima, como rede de segurança.
- **Ignorar em vez de falhar** para arquivo grande/patológico: um único arquivo gerado não deve invalidar
  a medição do repositório inteiro.

## Consequências

- Repositórios muito grandes (ou com conteúdo descompactado grande) passam a ser recusados com mensagem
  clara; os padrões podem ser elevados por configuração se a infraestrutura permitir.
- O prazo cooperativo só é verificado entre arquivos: uma única operação nativa muito longa dentro de um
  arquivo não é interrompida por ele (por isso os limites do Celery e o teto de 1 MB por arquivo).
- Fora do escopo desta mudança: arquivos gerados que *cabem* nos tetos (`*.min.js`, `.next/`, `target/`…)
  e a escolha do `coverage.xml` em monorepos (issue #100); o tratamento de falhas de rede/5xx do GitHub
  (issue #91); e o limite de análises ativas por repositório.
