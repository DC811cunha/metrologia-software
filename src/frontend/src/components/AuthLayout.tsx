import { ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { ChartIcon, DocumentIcon, GaugeIcon } from './ui/Icon';
import Logo from './ui/Logo';

interface AuthLayoutProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  /** Conteúdo abaixo do formulário — links de navegação entre telas de autenticação. */
  footer?: ReactNode;
}

const FEATURES = [
  { icon: GaugeIcon, text: '6 métricas de qualidade avaliadas por limiares objetivos' },
  { icon: ChartIcon, text: 'Histórico e tendência a cada nova análise' },
  { icon: DocumentIcon, text: 'Relatórios em PDF prontos para apresentar' },
];

function PreviewCard({
  label,
  value,
  status,
  statusClass,
  className,
}: {
  label: string;
  value: string;
  status: string;
  statusClass: string;
  className: string;
}) {
  return (
    <div
      className={`absolute w-52 rounded-2xl border border-white/15 bg-white/10 p-4 shadow-2xl backdrop-blur-md ${className}`}
    >
      <p className="text-xs font-medium text-brand-100">{label}</p>
      <p className="mt-1 text-2xl font-bold tabular-nums text-white">{value}</p>
      <span className={`status-dot mt-2 inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${statusClass}`}>
        {status}
      </span>
    </div>
  );
}

/**
 * Casca visual das telas de autenticação: painel de marca à esquerda (somente em telas
 * largas) e formulário à direita. Em telas pequenas, a marca vira um cabeçalho compacto.
 */
function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps) {
  return (
    <div className="min-h-screen bg-canvas lg:grid lg:grid-cols-[1.05fr_1fr]">
      <a href="#conteudo" className="skip-link">
        Pular para o conteúdo
      </a>

      <aside
        className="relative hidden overflow-hidden bg-gradient-to-br from-ink-950 via-brand-950 to-brand-700 p-10 text-white lg:flex lg:flex-col lg:justify-between xl:p-12"
      >
        <div aria-hidden="true" className="bg-grid absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_75%)]" />
        <div aria-hidden="true" className="absolute -right-24 -top-24 h-96 w-96 rounded-full bg-brand-500/30 blur-3xl" />
        <div aria-hidden="true" className="absolute -bottom-32 -left-20 h-96 w-96 rounded-full bg-cyan-400/15 blur-3xl" />

        {/* A logo é o caminho de volta à página inicial: fica fora das áreas decorativas (aria-hidden). */}
        <Link to="/" aria-label="SoftMeter — página inicial" className="relative w-fit rounded-lg">
          <Logo tone="light" />
        </Link>

        <div aria-hidden="true" className="relative max-w-lg">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-medium text-brand-100 backdrop-blur">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-300" />
            Metrologia aplicada ao software
          </span>
          <p className="mt-6 text-4xl font-extrabold leading-[1.1] tracking-tight xl:text-5xl xl:leading-[1.08]">
            Meça a qualidade do seu código com a precisão da indústria.
          </p>
          <p className="mt-5 text-base leading-relaxed text-brand-100/90">
            O SoftMeter analisa repositórios do GitHub e transforma métricas de engenharia em
            indicadores claros de conformidade.
          </p>

          <ul className="mt-8 flex flex-col gap-3.5">
            {FEATURES.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-sm text-brand-50">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10 ring-1 ring-white/15">
                  <Icon className="h-4 w-4 text-brand-200" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>

        {/* Pré-visualização decorativa: só aparece quando há altura suficiente */}
        <div aria-hidden="true" className="relative hidden h-48 [@media(min-height:860px)]:block">
          <PreviewCard
            label="Cobertura de Testes"
            value="87 %"
            status="Conforme"
            statusClass="bg-conforme-bg text-conforme-text"
            className="bottom-2 left-0 animate-float"
          />
          <PreviewCard
            label="Complexidade Ciclomática"
            value="14,2"
            status="Condicional"
            statusClass="bg-condicional-bg text-condicional-text"
            className="bottom-10 left-44 animate-float [animation-delay:1.5s]"
          />
          <PreviewCard
            label="Manutenibilidade"
            value="82"
            status="Conforme"
            statusClass="bg-conforme-bg text-conforme-text"
            className="-bottom-2 left-[22rem] hidden animate-float [animation-delay:3s] 2xl:block"
          />
        </div>
      </aside>

      <main id="conteudo" className="flex min-h-screen flex-col items-center justify-center px-5 py-10 sm:px-10">
        <div className="w-full max-w-md">
          <Link to="/" aria-label="SoftMeter — página inicial" className="mb-8 inline-block rounded-lg lg:hidden">
            <Logo />
          </Link>

          <div className="animate-fade-up rounded-3xl border border-brand-500/40 bg-gradient-to-b from-surface to-surface/70 p-7 shadow-neon sm:p-9">
            <h1 className="text-2xl font-extrabold text-fg">{title}</h1>
            <p className="mb-7 mt-1.5 text-sm leading-relaxed text-fg-muted">{subtitle}</p>
            {children}
          </div>

          {footer && <div className="mt-6 text-center text-sm text-fg-muted">{footer}</div>}
        </div>
      </main>
    </div>
  );
}

export default AuthLayout;
