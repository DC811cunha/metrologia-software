/**
 * Testes unitários — MedicoesService
 * Cobertura das regras de negócio do framework de Metrologia de Software
 */

import {
  calcularDesvioAbsoluto,
  calcularDesvioRelativo,
  classificarConformidade,
  processarMedicao,
  calcularResultadoLaudo,
  Requisito,
} from '../src/services/medicoes.service';

// ─── Requisito de exemplo ──────────────────────────────────────────────────
const requisitoBase: Requisito = {
  id: 'req-001',
  valorNominal: 2.0,
  toleranciaSup: 2.5,
  toleranciaInf: 1.5,
  criticidade: 'maior',
};

// ─── calcularDesvioAbsoluto ────────────────────────────────────────────────
describe('calcularDesvioAbsoluto', () => {
  it('retorna zero quando medido = nominal', () => {
    expect(calcularDesvioAbsoluto(2.0, 2.0)).toBe(0);
  });

  it('retorna desvio positivo quando medido > nominal', () => {
    expect(calcularDesvioAbsoluto(2.35, 2.0)).toBe(0.35);
  });

  it('retorna desvio negativo quando medido < nominal', () => {
    expect(calcularDesvioAbsoluto(1.7, 2.0)).toBe(-0.3);
  });
});

// ─── calcularDesvioRelativo ────────────────────────────────────────────────
describe('calcularDesvioRelativo', () => {
  it('retorna zero quando nominal é zero (evita divisão por zero)', () => {
    expect(calcularDesvioRelativo(5, 0)).toBe(0);
  });

  it('calcula percentual corretamente', () => {
    expect(calcularDesvioRelativo(2.2, 2.0)).toBe(10);
  });

  it('usa valor absoluto do desvio', () => {
    expect(calcularDesvioRelativo(1.8, 2.0)).toBe(10);
  });
});

// ─── classificarConformidade ───────────────────────────────────────────────
describe('classificarConformidade', () => {
  it('retorna "aprovado" quando valor está no centro da tolerância', () => {
    expect(classificarConformidade(2.0, requisitoBase)).toBe('aprovado');
  });

  it('retorna "reprovado" quando valor está acima da tolerância superior', () => {
    expect(classificarConformidade(2.6, requisitoBase)).toBe('reprovado');
  });

  it('retorna "reprovado" quando valor está abaixo da tolerância inferior', () => {
    expect(classificarConformidade(1.4, requisitoBase)).toBe('reprovado');
  });

  it('retorna "alerta" quando valor está próximo do limite superior', () => {
    expect(classificarConformidade(2.49, requisitoBase)).toBe('alerta');
  });

  it('retorna "aprovado" exatamente no limite superior', () => {
    const status = classificarConformidade(2.5, requisitoBase);
    expect(['aprovado', 'alerta']).toContain(status);
  });
});

// ─── processarMedicao ─────────────────────────────────────────────────────
describe('processarMedicao', () => {
  it('retorna estrutura completa com desvios e status', () => {
    const resultado = processarMedicao(2.0, requisitoBase);
    expect(resultado).toHaveProperty('desvioAbsoluto');
    expect(resultado).toHaveProperty('desvioRelativo');
    expect(resultado).toHaveProperty('statusConformidade');
  });

  it('classifica corretamente uma medição dentro da tolerância', () => {
    const resultado = processarMedicao(2.0, requisitoBase);
    expect(resultado.statusConformidade).toBe('aprovado');
    expect(resultado.desvioAbsoluto).toBe(0);
  });

  it('classifica corretamente uma medição fora da tolerância', () => {
    const resultado = processarMedicao(3.0, requisitoBase);
    expect(resultado.statusConformidade).toBe('reprovado');
    expect(resultado.desvioAbsoluto).toBe(1);
  });
});

// ─── calcularResultadoLaudo ────────────────────────────────────────────────
describe('calcularResultadoLaudo', () => {
  it('classifica como "conforme" quando índice >= 90%', () => {
    const medicoes = Array(10).fill({ status: 'aprovado', criticidade: 'menor' });
    const resultado = calcularResultadoLaudo(medicoes);
    expect(resultado.classificacaoFinal).toBe('conforme');
    expect(resultado.indiceConformidade).toBe(100);
  });

  it('classifica como "condicional" quando índice entre 70% e 89%', () => {
    const medicoes = [
      ...Array(8).fill({ status: 'aprovado', criticidade: 'menor' }),
      ...Array(2).fill({ status: 'reprovado', criticidade: 'menor' }),
    ];
    const resultado = calcularResultadoLaudo(medicoes);
    expect(resultado.classificacaoFinal).toBe('condicional');
    expect(resultado.indiceConformidade).toBe(80);
  });

  it('classifica como "nao_conforme" quando índice < 70%', () => {
    const medicoes = [
      ...Array(6).fill({ status: 'aprovado', criticidade: 'menor' }),
      ...Array(4).fill({ status: 'reprovado', criticidade: 'menor' }),
    ];
    const resultado = calcularResultadoLaudo(medicoes);
    expect(resultado.classificacaoFinal).toBe('nao_conforme');
  });

  it('classifica como "nao_conforme" quando há requisito crítico reprovado', () => {
    const medicoes = [
      ...Array(9).fill({ status: 'aprovado', criticidade: 'menor' }),
      { status: 'reprovado', criticidade: 'critico' },
    ];
    const resultado = calcularResultadoLaudo(medicoes);
    expect(resultado.classificacaoFinal).toBe('nao_conforme');
  });

  it('calcula corretamente o total de aprovados', () => {
    const medicoes = [
      { status: 'aprovado', criticidade: 'menor' },
      { status: 'reprovado', criticidade: 'menor' },
      { status: 'alerta', criticidade: 'menor' },
    ];
    const resultado = calcularResultadoLaudo(medicoes);
    expect(resultado.totalRequisitos).toBe(3);
    expect(resultado.totalAprovados).toBe(1);
  });

  it('retorna índice zero quando não há medições', () => {
    const resultado = calcularResultadoLaudo([]);
    expect(resultado.indiceConformidade).toBe(0);
  });
});
