/**
 * Tipos compartilhados do SoftMeter
 * Espelho das entidades do banco de dados
 */

export type Criticidade = 'critico' | 'maior' | 'menor';
export type StatusConformidade = 'aprovado' | 'alerta' | 'reprovado' | 'pendente';
export type ClassificacaoFinal = 'conforme' | 'condicional' | 'nao_conforme';
export type StatusCiclo = 'aberto' | 'encerrado';
export type StatusSistema = 'ativo' | 'arquivado';

export interface Usuario {
  id: string;
  nome: string;
  email: string;
  createdAt: Date;
}

export interface Sistema {
  id: string;
  idUsuario: string;
  nome: string;
  descricao?: string;
  responsavel?: string;
  status: StatusSistema;
  createdAt: Date;
}

export interface Requisito {
  id: string;
  idSistema: string;
  codigo: string;
  descricao: string;
  valorNominal: number;
  toleranciaSup: number;
  toleranciaInf: number;
  unidade: string;
  criticidade: Criticidade;
  ativo: boolean;
  createdAt: Date;
}

export interface CicloTeste {
  id: string;
  idSistema: string;
  versaoSoftware: string;
  ambiente?: string;
  status: StatusCiclo;
  dataInicio: Date;
  dataFim?: Date;
  createdAt: Date;
}

export interface Medicao {
  id: string;
  idCiclo: string;
  idRequisito: string;
  valorMedido: number;
  desvioAbsoluto: number;
  statusConformidade: StatusConformidade;
  observacao?: string;
  createdAt: Date;
}

export interface Laudo {
  id: string;
  idCiclo: string;
  totalRequisitos: number;
  totalAprovados: number;
  indiceConformidade: number;
  classificacaoFinal: ClassificacaoFinal;
  pdfUrl?: string;
  observacoesGerais?: string;
  createdAt: Date;
}

// DTOs de entrada
export interface CriarSistemaDTO {
  nome: string;
  descricao?: string;
  responsavel?: string;
}

export interface CriarRequisitoDTO {
  idSistema: string;
  codigo: string;
  descricao: string;
  valorNominal: number;
  toleranciaSup: number;
  toleranciaInf: number;
  unidade: string;
  criticidade: Criticidade;
}

export interface CriarCicloDTO {
  idSistema: string;
  versaoSoftware: string;
  ambiente?: string;
}

export interface CriarMedicaoDTO {
  idCiclo: string;
  idRequisito: string;
  valorMedido: number;
  observacao?: string;
}
