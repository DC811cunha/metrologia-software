/**
 * MedicoesService
 *
 * Contém as regras de negócio centrais do framework de Metrologia de Software:
 * - Cálculo de desvio absoluto e relativo
 * - Classificação de conformidade (Aprovado / Alerta / Reprovado)
 * - Cálculo do Índice de Conformidade Geral
 * - Classificação final do Laudo (Conforme / Condicional / Não-Conforme)
 */

export type StatusConformidade = 'aprovado' | 'alerta' | 'reprovado';
export type ClassificacaoFinal = 'conforme' | 'condicional' | 'nao_conforme';
export type Criticidade = 'critico' | 'maior' | 'menor';

export interface Requisito {
  id: string;
  valorNominal: number;
  toleranciaSup: number;
  toleranciaInf: number;
  criticidade: Criticidade;
}

export interface ResultadoMedicao {
  desvioAbsoluto: number;
  desvioRelativo: number;
  statusConformidade: StatusConformidade;
}

export interface ResultadoLaudo {
  totalRequisitos: number;
  totalAprovados: number;
  indiceConformidade: number;
  classificacaoFinal: ClassificacaoFinal;
}

/**
 * Calcula o desvio absoluto entre o valor medido e o nominal.
 */
export function calcularDesvioAbsoluto(valorMedido: number, valorNominal: number): number {
  return Number((valorMedido - valorNominal).toFixed(4));
}

/**
 * Calcula o desvio relativo percentual.
 * Evita divisão por zero quando o nominal é zero.
 */
export function calcularDesvioRelativo(valorMedido: number, valorNominal: number): number {
  if (valorNominal === 0) return 0;
  return Number(((Math.abs(valorMedido - valorNominal) / Math.abs(valorNominal)) * 100).toFixed(4));
}

/**
 * Classifica o status de conformidade de uma medição.
 *
 * Regras:
 * - Aprovado: valor medido dentro dos limites [toleranciaInf, toleranciaSup]
 * - Alerta: dentro de 95–100% dos limites (zona de atenção)
 * - Reprovado: fora dos limites de tolerância
 */
export function classificarConformidade(
  valorMedido: number,
  requisito: Pick<Requisito, 'valorNominal' | 'toleranciaSup' | 'toleranciaInf'>
): StatusConformidade {
  const { toleranciaSup, toleranciaInf } = requisito;

  if (valorMedido >= toleranciaInf && valorMedido <= toleranciaSup) {
    // Dentro da tolerância — verificar zona de alerta (5% das margens)
    const margemSup = toleranciaSup - requisito.valorNominal;
    const margemInf = requisito.valorNominal - toleranciaInf;
    const zonaAlertaSup = toleranciaSup - margemSup * 0.05;
    const zonaAlertaInf = toleranciaInf + margemInf * 0.05;

    if (valorMedido > zonaAlertaSup || valorMedido < zonaAlertaInf) {
      return 'alerta';
    }
    return 'aprovado';
  }

  return 'reprovado';
}

/**
 * Processa uma medição completa e retorna desvios + status.
 */
export function processarMedicao(valorMedido: number, requisito: Requisito): ResultadoMedicao {
  return {
    desvioAbsoluto: calcularDesvioAbsoluto(valorMedido, requisito.valorNominal),
    desvioRelativo: calcularDesvioRelativo(valorMedido, requisito.valorNominal),
    statusConformidade: classificarConformidade(valorMedido, requisito),
  };
}

/**
 * Calcula o Índice de Conformidade Geral e a Classificação Final do Laudo.
 *
 * Regras de classificação:
 * - Conforme: índice >= 90%
 * - Condicional: índice entre 70% e 89%
 * - Não-Conforme: índice < 70%
 * - Exceção: qualquer requisito CRÍTICO reprovado → Não-Conforme imediato
 */
export function calcularResultadoLaudo(
  medicoes: Array<{ status: StatusConformidade; criticidade: Criticidade }>
): ResultadoLaudo {
  const totalRequisitos = medicoes.length;
  const totalAprovados = medicoes.filter((m) => m.status === 'aprovado').length;
  const indiceConformidade = totalRequisitos > 0
    ? Number(((totalAprovados / totalRequisitos) * 100).toFixed(2))
    : 0;

  // Exceção: crítico reprovado → Não-Conforme imediato
  const temCriticoReprovado = medicoes.some(
    (m) => m.criticidade === 'critico' && m.status === 'reprovado'
  );

  let classificacaoFinal: ClassificacaoFinal;
  if (temCriticoReprovado || indiceConformidade < 70) {
    classificacaoFinal = 'nao_conforme';
  } else if (indiceConformidade < 90) {
    classificacaoFinal = 'condicional';
  } else {
    classificacaoFinal = 'conforme';
  }

  return { totalRequisitos, totalAprovados, indiceConformidade, classificacaoFinal };
}
