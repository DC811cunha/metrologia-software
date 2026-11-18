# ADR-015: Pastas Ambíguas por Contexto, Acoplamento Indefinido e Índice de Manutenibilidade Ponderado

**Data:** 18/11/2026
**Status:** Aceito
**Autor:** Diego Cunha
**Origem:** revisão geral de 18/11/2026 (pontos 1 e 3 da lista de pendências)

---

## Contexto

Três decisões de métrica ainda produziam valores enganosos:

1. **Pastas com nome ambíguo.** O ADR-011 podava `build`, `dist`, `out`, `target`, `coverage`, `env` e `vendor` **em qualquer
   profundidade**. O zip que o SoftMeter baixa do GitHub só contém arquivos versionados, então esses nomes só importam
   quando alguém commitou saída de build — mas, como a poda era por nome, um pacote de código legítimo chamado `build`
   (`src/ferramenta/build/`, de uma ferramenta de build) ou um `env/` de configuração sumia da medição em silêncio.
2. **Acoplamento de um módulo só.** A instabilidade `I = Ce / (Ce + Ca)` é `0/0` quando não há aresta interna. O ADR-010
   já devolvia "Não disponível" para vários módulos sem imports resolvidos, mas mantinha `0.0` ("Conforme") para um único
   módulo — um valor que parece uma medição e não é.
3. **Média do Índice de Manutenibilidade por arquivo, sem peso.** Um arquivo de uma linha (um `__init__.py`, uma
   constante) rende MI próximo de 100 e pesava o mesmo que um módulo de 500 linhas, inflando a média de repositórios cujo
   código está em poucos arquivos grandes.

## Decisão

**Pastas ambíguas por contexto.** Continuam podadas sempre: `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`,
`site-packages`, `bower_components`, `.next`, `.nuxt`, `vendor`, `.tox`, `migrations` e os diretórios de teste. Os nomes
`build`, `dist`, `out`, `target` e `coverage` só são podados quando há evidência de que são **saída**: estão na raiz do
repositório ou ao lado de um manifesto de projeto (`package.json`, `pyproject.toml`, `setup.py`, `setup.cfg`,
`requirements.txt`, `tsconfig.json`, `pom.xml`, `build.gradle[.kts]`, `Cargo.toml`). `env/` só é podada se for um ambiente
virtual de fato (tem `pyvenv.cfg`). Arquivos gerados que sobrarem seguem filtrados por nome e forma (`*.min.js`, `*.d.ts`,
bundles minificados — ADR-011).

**Acoplamento indefinido.** Sem nenhuma aresta interna resolvida a métrica é **"Não disponível"**, seja com um módulo
ou com vários. Reverte a exceção do módulo único do ADR-010.

**MI ponderado por linhas.** A média do repositório passa a pesar o MI de cada arquivo pelo seu SLOC
(`Σ MI·SLOC / Σ SLOC`) — a mesma convenção de agregação do Visual Studio. O MI de cada arquivo e os limites
(≥ 20 Conforme, ≥ 10 Condicional) não mudam.

## Consequências

- **Os valores mudam, e o do MI muda bastante.** Medido em repositórios reais (média simples → ponderada por SLOC):
  `pypa/sampleproject` 94,3 → 94,3 (2 arquivos, sem efeito); `pallets/click` 60,5 → **32,8**; `psf/requests` 69,3 →
  **30,3**; o próprio SoftMeter 51,8 → **29,8**. Todos continuam Conformes (≥ 20), mas mais perto do limite: o número
  agora descreve onde está a massa do código, não o arquivo médio. Repositórios com poucos arquivos enormes podem passar a
  Condicional.
- **O histórico ganha um degrau**, como nos ADRs 010 e 011: análises já gravadas **não** são recalculadas. Quem compara a
  análise de antes e a de depois desta mudança vê o MI cair sem que o código tenha piorado.
- Repositório de um único módulo passa a mostrar Acoplamento "Não disponível" e a métrica sai do índice geral.
- Repositórios com `src/**/build/` (ou outro nome ambíguo fora da raiz e de manifestos) passam a ter esse código medido.
- A descrição do MI no catálogo (e, portanto, no PDF e no dashboard) passa a dizer que a média é ponderada pelas linhas.
