import { render, screen } from '@testing-library/react';

import Gauge from '../src/components/Gauge';

const BANDS = [
  { upTo: 10, color: '#16a34a' },
  { upTo: 20, color: '#d97706' },
  { upTo: 30, color: '#dc2626' },
];

describe('Gauge', () => {
  it('renders the label, value with unit, and status', () => {
    render(
      <Gauge
        label="Complexidade Ciclomática"
        value={5}
        unit="caminhos/função"
        min={0}
        max={30}
        bands={BANDS}
        statusLabel="Conforme"
      />,
    );

    expect(screen.getByText('Complexidade Ciclomática')).toBeInTheDocument();
    expect(screen.getByText('5 caminhos/função')).toBeInTheDocument();
    expect(screen.getByText('Conforme')).toBeInTheDocument();
  });

  it('shows "Não disponível" and hides the needle when value is null', () => {
    render(
      <Gauge
        label="Cobertura de Testes"
        value={null}
        unit="%"
        min={0}
        max={100}
        bands={BANDS}
        statusLabel="Não disponível"
      />,
    );

    expect(screen.getAllByText('Não disponível')).toHaveLength(2);
    expect(screen.queryByTestId('gauge-needle')).not.toBeInTheDocument();
  });

  it('points the needle straight up when the value is at the midpoint', () => {
    render(
      <Gauge
        label="Acoplamento"
        value={15}
        unit=""
        min={0}
        max={30}
        bands={BANDS}
        statusLabel="Condicional"
      />,
    );

    expect(screen.getByTestId('gauge-needle')).toHaveStyle({
      transform: 'translateX(-50%) rotate(0deg)',
    });
  });

  it('clamps the needle angle for values above the configured max', () => {
    render(
      <Gauge label="LOC" value={999} unit="" min={0} max={30} bands={BANDS} statusLabel="Não-Conforme" />,
    );

    expect(screen.getByTestId('gauge-needle')).toHaveStyle({
      transform: 'translateX(-50%) rotate(90deg)',
    });
  });
});
