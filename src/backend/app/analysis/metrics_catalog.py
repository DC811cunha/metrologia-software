"""Catálogo fixo das métricas suportadas (Constituição, Princípio V).

Nenhuma Medição pode ser exibida sem que sua métrica esteja completamente
definida aqui: nome, unidade, fórmula, fonte bibliográfica e limites de
especificação. Ver specs/001-softmeter-plataforma-mvp/data-model.md.
"""

from dataclasses import dataclass
from enum import Enum


class ConformityStatus(str, Enum):
    CONFORME = "Conforme"
    CONDICIONAL = "Condicional"
    NAO_CONFORME = "Não-Conforme"
    NAO_DISPONIVEL = "Não disponível"


class Direcao(str, Enum):
    MAIOR_MELHOR = "maior_melhor"
    MENOR_MELHOR = "menor_melhor"


@dataclass(frozen=True)
class MetricDefinition:
    chave: str
    nome: str
    unidade: str
    formula: str
    fonte_bibliografica: str
    limite_nominal: float
    limite_superior_condicional: float
    direcao: Direcao = Direcao.MENOR_MELHOR
    permite_nao_disponivel: bool = False

    def classificar(self, valor: float | None) -> ConformityStatus:
        if valor is None:
            if self.permite_nao_disponivel:
                return ConformityStatus.NAO_DISPONIVEL
            raise ValueError(f"Métrica '{self.chave}' não permite valor ausente")
        if self.direcao is Direcao.MAIOR_MELHOR:
            if valor >= self.limite_nominal:
                return ConformityStatus.CONFORME
            if valor >= self.limite_superior_condicional:
                return ConformityStatus.CONDICIONAL
            return ConformityStatus.NAO_CONFORME
        if valor <= self.limite_nominal:
            return ConformityStatus.CONFORME
        if valor <= self.limite_superior_condicional:
            return ConformityStatus.CONDICIONAL
        return ConformityStatus.NAO_CONFORME


# Escopo da medição (ADR-011), exibido ao usuário no relatório PDF e no dashboard — o texto do
# dashboard fica em `frontend/src/metricsCatalog.ts` e deve acompanhar este.
SCOPE_NOTE = (
    "Escopo da medição: as métricas de código (complexidade ciclomática, LOC, índice de "
    "manutenibilidade, acoplamento e duplicação) consideram apenas o código-fonte de produção. "
    "Arquivos de teste, dependências e arquivos gerados ou minificados não entram nelas. "
    "A cobertura de testes é lida dos relatórios publicados pelo próprio repositório."
)

METRICS_CATALOG: dict[str, MetricDefinition] = {
    "complexidade_ciclomatica": MetricDefinition(
        chave="complexidade_ciclomatica",
        nome="Complexidade Ciclomática",
        unidade="nº de caminhos / função (média do repositório)",
        formula="CC = E - N + 2P (arestas - nós + 2×componentes conexos do grafo de fluxo de controle), por função/método; mede o código de produção (testes, dependências e arquivos gerados/minificados ficam de fora)",
        fonte_bibliografica="McCabe, T.J. (1976). A Complexity Measure. IEEE Trans. Software Engineering; NIST SP 500-235",
        limite_nominal=10,
        limite_superior_condicional=20,
    ),
    "loc": MetricDefinition(
        chave="loc",
        nome="Linhas de Código (LOC)",
        unidade="linhas / função (média do repositório)",
        formula="Contagem de linhas físicas de código (SLOC), excluindo comentários e linhas em branco, por função/método — mesma convenção em Python e JS/TS e na entrada do Índice de Manutenibilidade",
        fonte_bibliografica="Martin, R.C. (2008). Clean Code",
        limite_nominal=30,
        limite_superior_condicional=60,
    ),
    "indice_manutenibilidade": MetricDefinition(
        chave="indice_manutenibilidade",
        nome="Índice de Manutenibilidade",
        unidade="escala 0-100 (por arquivo, média do repositório)",
        formula="MI = 171 - 5.2*ln(HV) - 0.23*CC - 16.2*ln(LOC), normalizado 0-100",
        fonte_bibliografica="Coleman, D. et al. (1994). Using Metrics to Evaluate Software System Maintainability. IEEE Computer; ranks da ferramenta Radon",
        limite_nominal=20,
        limite_superior_condicional=10,
        direcao=Direcao.MAIOR_MELHOR,
    ),
    "cobertura_testes": MetricDefinition(
        chave="cobertura_testes",
        nome="Cobertura de Testes",
        unidade="% de linhas cobertas",
        formula="Percentual relatado em artefato de cobertura já publicado no repositório (coverage.xml, lcov.info, badge Codecov/Coveralls)",
        fonte_bibliografica="Relatórios coverage.py/lcov; limites alinhados ao Princípio I da Constituição SoftMeter",
        limite_nominal=80,
        limite_superior_condicional=50,
        direcao=Direcao.MAIOR_MELHOR,
        permite_nao_disponivel=True,
    ),
    "acoplamento": MetricDefinition(
        chave="acoplamento",
        nome="Acoplamento (Instabilidade de Módulo)",
        unidade="razão 0-1 (média do repositório)",
        formula="I = Ce / (Ce + Ca) — Ce = acoplamento de saída (imports internos), Ca = acoplamento de entrada; imports resolvidos por sufixo de caminho (Python) e por tsconfig/jsconfig (JS/TS). Não disponível se nenhum import interno for resolvido",
        fonte_bibliografica="Martin, R.C. (2002). Agile Software Development: Principles, Patterns, and Practices",
        limite_nominal=0.70,
        limite_superior_condicional=0.85,
        # "Não disponível" quando nenhum import interno é resolvido em um repositório com vários
        # módulos (ver analysis/coupling.py): 0.0 seria indistinguível de "não consegui resolver".
        permite_nao_disponivel=True,
    ),
    "score_duplicacao": MetricDefinition(
        chave="score_duplicacao",
        nome="Score de Duplicação",
        unidade="% de linhas duplicadas",
        formula="Percentual de linhas em blocos de código duplicados (Tipo-1/Tipo-2) via shingling de tokens normalizados, janela mínima de 6 linhas com ao menos 4 linhas distintas; imports não contam e janelas sobrepostas do mesmo arquivo não casam entre si",
        fonte_bibliografica="Abordagem equivalente à métrica Duplicated Lines Density da SonarSource",
        limite_nominal=5,
        limite_superior_condicional=15,
    ),
}


def get_metric(chave: str) -> MetricDefinition:
    return METRICS_CATALOG[chave]
