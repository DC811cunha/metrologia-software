import pytest

from app.analysis.metrics_catalog import METRICS_CATALOG, ConformityStatus, get_metric


@pytest.mark.parametrize(
    "chave,valor,esperado",
    [
        ("complexidade_ciclomatica", 5, ConformityStatus.CONFORME),
        ("complexidade_ciclomatica", 15, ConformityStatus.CONDICIONAL),
        ("complexidade_ciclomatica", 25, ConformityStatus.NAO_CONFORME),
        ("loc", 10, ConformityStatus.CONFORME),
        ("score_duplicacao", 2, ConformityStatus.CONFORME),
        ("score_duplicacao", 20, ConformityStatus.NAO_CONFORME),
        ("acoplamento", 0.5, ConformityStatus.CONFORME),
        ("acoplamento", 0.9, ConformityStatus.NAO_CONFORME),
    ],
)
def test_classificacao_menor_melhor(chave, valor, esperado):
    assert get_metric(chave).classificar(valor) is esperado


@pytest.mark.parametrize(
    "valor,esperado",
    [
        (90, ConformityStatus.CONFORME),
        (60, ConformityStatus.CONDICIONAL),
        (20, ConformityStatus.NAO_CONFORME),
    ],
)
def test_cobertura_testes_classificacao_maior_melhor(valor, esperado):
    assert get_metric("cobertura_testes").classificar(valor) is esperado


@pytest.mark.parametrize(
    "valor,esperado",
    [
        (25, ConformityStatus.CONFORME),
        (15, ConformityStatus.CONDICIONAL),
        (5, ConformityStatus.NAO_CONFORME),
    ],
)
def test_indice_manutenibilidade_classificacao_maior_melhor(valor, esperado):
    assert get_metric("indice_manutenibilidade").classificar(valor) is esperado


def test_cobertura_testes_aceita_nao_disponivel():
    assert get_metric("cobertura_testes").classificar(None) is ConformityStatus.NAO_DISPONIVEL


def test_metrica_sem_permitir_nao_disponivel_levanta_erro():
    with pytest.raises(ValueError):
        get_metric("complexidade_ciclomatica").classificar(None)


def test_catalogo_tem_as_6_metricas_com_definicao_completa():
    assert len(METRICS_CATALOG) == 6
    for metrica in METRICS_CATALOG.values():
        assert metrica.nome
        assert metrica.unidade
        assert metrica.formula
        assert metrica.fonte_bibliografica
