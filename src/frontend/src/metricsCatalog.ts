import { GaugeBand } from './components/Gauge';

const CONFORME = '#22c55e';
const CONDICIONAL = '#f59e0b';
const NAO_CONFORME = '#ef4444';

/**
 * Escopo da medição (ADR-011), exibido no dashboard. Deve acompanhar `SCOPE_NOTE` do backend
 * (`app/analysis/metrics_catalog.py`), que vai no relatório PDF.
 */
export const SCOPE_NOTE =
  'Arquivos de teste, dependências e arquivos gerados ou minificados não entram nas métricas de código. ' +
  'A cobertura de testes é lida dos relatórios publicados pelo próprio repositório.';

export interface MetricGaugeConfig {
  chave: string;
  label: string;
  unidade: string;
  min: number;
  max: number;
  bands: GaugeBand[];
}

/**
 * Metadados de apresentação (rótulo, unidade, faixas de cor) para os 6 gauges do
 * dashboard — a classificação real (status_conformidade) vem sempre do backend;
 * isto só define a escala visual do gauge.
 */
export const METRICS_GAUGE_CONFIG: MetricGaugeConfig[] = [
  {
    chave: 'complexidade_ciclomatica',
    label: 'Complexidade Ciclomática',
    unidade: 'cam./função',
    min: 0,
    max: 30,
    bands: [
      { upTo: 10, color: CONFORME },
      { upTo: 20, color: CONDICIONAL },
      { upTo: 30, color: NAO_CONFORME },
    ],
  },
  {
    chave: 'loc',
    label: 'Linhas de Código (LOC)',
    unidade: 'linhas/função',
    min: 0,
    max: 90,
    bands: [
      { upTo: 30, color: CONFORME },
      { upTo: 60, color: CONDICIONAL },
      { upTo: 90, color: NAO_CONFORME },
    ],
  },
  {
    chave: 'indice_manutenibilidade',
    label: 'Índice de Manutenibilidade',
    unidade: '',
    min: 0,
    max: 100,
    bands: [
      { upTo: 10, color: NAO_CONFORME },
      { upTo: 20, color: CONDICIONAL },
      { upTo: 100, color: CONFORME },
    ],
  },
  {
    chave: 'cobertura_testes',
    label: 'Cobertura de Testes',
    unidade: '%',
    min: 0,
    max: 100,
    bands: [
      { upTo: 50, color: NAO_CONFORME },
      { upTo: 80, color: CONDICIONAL },
      { upTo: 100, color: CONFORME },
    ],
  },
  {
    chave: 'acoplamento',
    label: 'Acoplamento (Instabilidade)',
    unidade: '',
    min: 0,
    max: 1,
    bands: [
      { upTo: 0.7, color: CONFORME },
      { upTo: 0.85, color: CONDICIONAL },
      { upTo: 1, color: NAO_CONFORME },
    ],
  },
  {
    chave: 'score_duplicacao',
    label: 'Score de Duplicação',
    unidade: '%',
    min: 0,
    max: 30,
    bands: [
      { upTo: 5, color: CONFORME },
      { upTo: 15, color: CONDICIONAL },
      { upTo: 30, color: NAO_CONFORME },
    ],
  },
];
