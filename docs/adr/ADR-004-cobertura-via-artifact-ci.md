# ADR-004: Leitura de Cobertura de Testes via Artifact do GitHub Actions

**Data:** 16/09/2026
**Status:** Aceito
**Autor:** Diego Cunha

---

## Contexto

O `research.md` (item 6) já havia decidido, desde o planejamento inicial, que o SoftMeter
**nunca executa** a suíte de testes do repositório analisado — instalar dependências e rodar
código de terceiros vindo de qualquer URL pública do GitHub é uma superfície de execução
arbitrária que o projeto rejeitou por segurança. Em vez disso, a métrica de Cobertura de Testes
lia apenas artefatos **versionados no próprio código-fonte**: `coverage.xml`, `lcov.info` ou um
badge de percentual no `README.md`.

Na prática, isso deixava a métrica marcada como "Não disponível" na maioria absoluta das
análises reais — inclusive ao analisar o próprio SoftMeter. O motivo é simples: artefato de
cobertura é saída de build, e a prática recomendada (que o próprio projeto segue) é **não**
versionar saída de build. O `.gitignore` do SoftMeter exclui `.coverage`, `htmlcov/` e
`coverage/` — os mesmos arquivos que a métrica tentava encontrar no repositório.

## Decisão

Adicionar uma fonte de leitura **antes** das já existentes: o artifact de cobertura mais
recente que o próprio **GitHub Actions do repositório analisado** já publicou. A ideia central:
se o repositório tem CI configurado, ele quase sempre já rodou a suíte de testes e guardou o
resultado como artifact (é exatamente o que o workflow do próprio SoftMeter faz, publicando
`backend-coverage` e `frontend-coverage` a cada push). O SoftMeter passa a **baixar esse
resultado já pronto**, sem executar nada — a mesma garantia de segurança do `research.md` item 6
continua valendo integralmente.

A ordem de busca da métrica passa a ser:

```
1. Artifact do GitHub Actions do repositório      (novo — este ADR)
   com "coverage" no nome, não expirado
        │  não encontrado / sem token / erro de API
        ▼
2. coverage.xml versionado no código-fonte         (já existia)
        │  não encontrado
        ▼
3. lcov.info versionado no código-fonte            (já existia)
        │  não encontrado
        ▼
4. Badge de percentual no README.md                (já existia)
        │  não encontrado
        ▼
   "Não disponível" — excluído do índice agregado
```

Cada etapa só é tentada se a anterior não encontrar nada; qualquer falha (rede, token ausente,
artifact expirado) é silenciosa e cai para a próxima — a análise nunca é interrompida por causa
disso.

## Justificativa

- **Mantém a decisão de segurança original intacta.** Baixar um artifact é ler um arquivo que o
  CI do próprio dono do repositório já gerou publicamente — não é diferente, em termos de
  superfície de risco, de ler o `README.md`. Em nenhum momento o SoftMeter instala dependências
  ou executa um comando do repositório analisado.
- **Resolve o problema na causa raiz, não com uma exceção.** Em vez de tratar "o próprio
  SoftMeter não aparece com cobertura" como um caso especial, a mudança beneficia **qualquer**
  repositório analisado que tenha CI configurado — o que é muito mais comum do que versionar
  artefato de build.
- **Custo de infraestrutura pequeno e opcional.** A única exigência nova é um `GITHUB_TOKEN`
  (a API de artifacts do GitHub exige autenticação mesmo em repositórios públicos — diferente do
  download do código-fonte, que já funcionava sem token). Sem o token configurado, esta fonte é
  simplesmente pulada; nada quebra, o sistema só volta a se comportar como antes.

## Consequências

- **Requer configuração adicional em produção/demo**: variável `GITHUB_TOKEN` no ambiente do
  backend e do worker Celery, com um Personal Access Token que tenha o escopo `repo` (classic) ou
  a permissão "Actions: Read-only" (fine-grained) — o escopo restrito `public_repo` **não** é
  suficiente para baixar (só para listar) artifacts, mesmo em repositórios públicos.
- **Cobertura ainda pode legitimamente não aparecer.** Repositórios sem CI configurado, ou cujo
  artifact mais recente já expirou (padrão do GitHub: 90 dias), continuam corretamente mostrando
  "Não disponível" — isto não é uma regressão, é o mesmo comportamento documentado no
  `research.md` item 6 para quando nenhuma fonte está disponível.
- **`app/models/__init__.py` passou a centralizar o import de todos os modelos.** Efeito colateral
  necessário: o processo do worker Celery, ao ganhar uma nova chamada de rede antes só feita pelo
  processo do backend, expôs uma resolução de mapeamento SQLAlchemy (`Mapped["User"]`) que
  dependia "por acidente" de outro módulo já ter importado todas as classes antes. Corrigido na
  raiz em vez de remendado no worker.
- Validado com quatro cenários reais (nenhuma fonte disponível, artefato versionado, artifact de
  terceiro, artifact do próprio SoftMeter) antes de aceitar esta decisão.
