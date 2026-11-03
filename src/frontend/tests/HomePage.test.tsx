import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import HomePage from '../src/pages/HomePage';
import { METRICS_GAUGE_CONFIG } from '../src/metricsCatalog';

jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: { post: jest.fn() },
  ACCESS_TOKEN_KEY: 'softmeter_token',
}));

function renderHome() {
  return render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  );
}

describe('HomePage', () => {
  afterEach(() => {
    localStorage.clear();
  });

  describe('visitante', () => {
    it('apresenta o SoftMeter com um título principal', () => {
      renderHome();

      expect(
        screen.getByRole('heading', { level: 1, name: /meça a qualidade do seu código/i }),
      ).toBeInTheDocument();
    });

    it('leva ao cadastro e ao login pelos botões de ação', () => {
      renderHome();

      expect(screen.getByRole('link', { name: 'Começar agora' })).toHaveAttribute('href', '/register');
      expect(screen.getByRole('link', { name: 'Já tenho conta' })).toHaveAttribute('href', '/login');
      const header = screen.getByRole('banner');
      expect(within(header).getByRole('link', { name: 'Entrar' })).toHaveAttribute('href', '/login');
      expect(within(header).getByRole('link', { name: 'Criar conta' })).toHaveAttribute('href', '/register');
    });

    it('não oferece o acesso direto à plataforma', () => {
      renderHome();

      expect(screen.queryByRole('link', { name: 'Ir para a plataforma' })).not.toBeInTheDocument();
    });
  });

  describe('usuário autenticado', () => {
    it('troca os botões de cadastro/login por um atalho para a plataforma', () => {
      localStorage.setItem('softmeter_token', 'fake-token');

      renderHome();

      const links = screen.getAllByRole('link', { name: 'Ir para a plataforma' });
      expect(links.length).toBeGreaterThan(0);
      links.forEach((link) => expect(link).toHaveAttribute('href', '/repositories'));
      expect(screen.queryByRole('link', { name: 'Começar agora' })).not.toBeInTheDocument();
    });
  });

  describe('conteúdo', () => {
    it('lista as quatro etapas de uso', () => {
      renderHome();

      const steps = within(screen.getByRole('heading', { name: /do repositório ao relatório/i }).closest('section')!)
        .getAllByRole('listitem');
      expect(steps).toHaveLength(4);
    });

    it('descreve as seis métricas do catálogo', () => {
      renderHome();

      const section = screen.getByRole('heading', { name: /seis indicadores de qualidade/i }).closest('section')!;
      METRICS_GAUGE_CONFIG.forEach((config) => {
        expect(within(section).getByRole('heading', { name: config.label })).toBeInTheDocument();
      });
    });

    it('traz as perguntas frequentes', () => {
      renderHome();

      expect(screen.getByText('O SoftMeter executa o código do meu repositório?')).toBeInTheDocument();
      expect(screen.getAllByRole('group', { hidden: true }).length).toBeGreaterThan(0);
    });
  });

  describe('carrossel de tutorial', () => {
    function carousel() {
      return screen.getByRole('region', { name: 'Tutorial passo a passo' });
    }

    it('começa no primeiro passo', () => {
      renderHome();

      expect(within(carousel()).getByRole('group', { name: '1 de 6' })).toBeInTheDocument();
      expect(within(carousel()).queryByRole('group', { name: '2 de 6' })).not.toBeInTheDocument();
    });

    it('avança e volta com os botões, dando a volta nas pontas', () => {
      renderHome();

      fireEvent.click(screen.getByRole('button', { name: 'Próximo passo' }));
      expect(within(carousel()).getByRole('group', { name: '2 de 6' })).toBeInTheDocument();

      fireEvent.click(screen.getByRole('button', { name: 'Passo anterior' }));
      fireEvent.click(screen.getByRole('button', { name: 'Passo anterior' }));
      expect(within(carousel()).getByRole('group', { name: '6 de 6' })).toBeInTheDocument();
    });

    it('vai direto a um passo pelos indicadores', () => {
      renderHome();

      fireEvent.click(screen.getByRole('button', { name: /ir para o passo 4/i }));

      expect(within(carousel()).getByRole('group', { name: '4 de 6' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /ir para o passo 4/i })).toHaveAttribute('aria-current', 'step');
    });

    it('responde às setas do teclado', () => {
      renderHome();

      fireEvent.keyDown(carousel(), { key: 'ArrowRight' });
      expect(within(carousel()).getByRole('group', { name: '2 de 6' })).toBeInTheDocument();

      fireEvent.keyDown(carousel(), { key: 'ArrowLeft' });
      expect(within(carousel()).getByRole('group', { name: '1 de 6' })).toBeInTheDocument();
    });

    it('responde ao gesto de arrastar', () => {
      renderHome();

      fireEvent.touchStart(carousel(), { touches: [{ clientX: 300 }] });
      fireEvent.touchEnd(carousel(), { changedTouches: [{ clientX: 120 }] });

      expect(within(carousel()).getByRole('group', { name: '2 de 6' })).toBeInTheDocument();
    });
  });
});
