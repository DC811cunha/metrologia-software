import { ReactNode } from 'react';
import { Link } from 'react-router-dom';

import BrowserFrame from '../components/home/BrowserFrame';
import {
  DIFFERENTIALS,
  FAQ,
  JOURNEY,
  METRIC_INFO,
  SCREENS,
  TUTORIAL,
} from '../components/home/content';
import Reveal from '../components/home/Reveal';
import TutorialCarousel from '../components/home/TutorialCarousel';
import {
  ArrowRightIcon,
  ChartIcon,
  DocumentIcon,
  GaugeIcon,
  GithubIcon,
  ShieldIcon,
} from '../components/ui/Icon';
import Logo from '../components/ui/Logo';
import { METRICS_GAUGE_CONFIG, MetricGaugeConfig } from '../metricsCatalog';
import { ACCESS_TOKEN_KEY } from '../services/api';

const REPO_URL = 'https://github.com/DC811cunha/metrologia-software';

const PRIMARY_LINK =
  'inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg bg-gradient-to-b from-brand-500 to-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-brand transition-all hover:from-brand-400 hover:to-brand-600 hover:shadow-neon active:translate-y-px';
const SECONDARY_LINK =
  'inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg border border-line-strong bg-white/[0.04] px-5 py-2.5 text-sm font-semibold text-fg-soft transition-all hover:border-brand-400/60 hover:bg-brand-500/10 hover:text-fg active:translate-y-px';

const NAV_ITEMS = [
  { href: '#o-que-e', label: 'O que é' },
  { href: '#como-funciona', label: 'Como funciona' },
  { href: '#metricas', label: 'Métricas' },
  { href: '#tutorial', label: 'Tutorial' },
  { href: '#faq', label: 'Perguntas' },
];

const ANALOGY = [
  { from: 'Instrumento de medição', to: 'Motor de métricas', text: 'Lê o código-fonte e produz valores objetivos, sempre pelo mesmo método.' },
  { from: 'Tolerância e padrão', to: 'Limiares de conformidade', text: 'Cada valor é comparado a faixas definidas: Conforme, Condicional ou Não-Conforme.' },
  { from: 'Certificado de calibração', to: 'Relatório técnico em PDF', text: 'O resultado vira um documento que pode ser guardado e compartilhado.' },
];

const DIFFERENTIAL_ICONS = [ShieldIcon, GaugeIcon, ChartIcon, DocumentIcon];

function SectionHeading({ eyebrow, title, text }: { eyebrow: string; title: string; text?: string }) {
  return (
    <div className="mx-auto max-w-2xl text-center">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-400">{eyebrow}</p>
      <h2 className="mt-3 text-3xl font-extrabold text-fg sm:text-4xl">{title}</h2>
      {text && <p className="mt-4 text-base leading-relaxed text-fg-muted">{text}</p>}
    </div>
  );
}

function Section({ id, children }: { id: string; children: ReactNode }) {
  return (
    <section id={id} className="mx-auto w-full max-w-6xl scroll-mt-20 px-4 py-20 sm:px-6">
      {children}
    </section>
  );
}

/** Barra com as faixas de conformidade da métrica, geradas do mesmo catálogo dos gauges. */
function BandBar({ config }: { config: MetricGaugeConfig }) {
  const span = config.max - config.min;
  return (
    <div aria-hidden="true">
      <div className="flex h-2 gap-0.5 overflow-hidden rounded-full">
        {config.bands.map((band, index) => {
          const start = index === 0 ? config.min : config.bands[index - 1].upTo;
          return (
            <span
              key={band.upTo}
              style={{ width: `${((band.upTo - start) / span) * 100}%`, backgroundColor: band.color }}
              className="block"
            />
          );
        })}
      </div>
      <div className="mt-1.5 flex justify-between text-[11px] tabular-nums text-fg-subtle">
        <span>{config.min}</span>
        <span>{config.unidade ? `${config.max} ${config.unidade}` : config.max}</span>
      </div>
    </div>
  );
}

function HomePage() {
  const isAuthenticated = Boolean(localStorage.getItem(ACCESS_TOKEN_KEY));

  return (
    <div className="min-h-screen">
      <a href="#conteudo" className="skip-link">
        Pular para o conteúdo
      </a>

      <header className="sticky top-0 z-40 border-b border-line bg-canvas/75 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link to="/" aria-label="SoftMeter — página inicial" className="rounded-lg">
            <Logo tone="light" />
          </Link>

          <nav aria-label="Seções da página" className="hidden items-center gap-1 lg:flex">
            {NAV_ITEMS.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="rounded-lg px-3 py-2 text-sm font-medium text-fg-muted transition-colors hover:bg-white/5 hover:text-fg"
              >
                {item.label}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            {isAuthenticated ? (
              <Link to="/repositories" className={PRIMARY_LINK}>
                Ir para a plataforma
              </Link>
            ) : (
              <>
                <Link to="/login" className={`${SECONDARY_LINK} !px-4`}>
                  Entrar
                </Link>
                <Link to="/register" className={`${PRIMARY_LINK} hidden !px-4 sm:inline-flex`}>
                  Criar conta
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main id="conteudo">
        {/* ── Hero ───────────────────────────────────────────── */}
        <div className="relative overflow-hidden">
          <div className="bg-grid pointer-events-none absolute inset-0 opacity-60 [mask-image:radial-gradient(ellipse_at_top,black_20%,transparent_70%)]" />
          <div className="pointer-events-none absolute -top-32 left-1/2 h-[28rem] w-[28rem] -translate-x-1/2 rounded-full bg-brand-500/25 blur-3xl" />

          <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-4 pb-16 pt-16 sm:px-6 lg:grid-cols-[1fr_1.1fr] lg:pb-24 lg:pt-24">
            <div className="animate-fade-up">
              <span className="inline-flex items-center gap-2 rounded-full border border-brand-400/30 bg-brand-500/10 px-3 py-1 text-xs font-medium text-brand-200">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-300" />
                Metrologia aplicada ao software
              </span>
              <h1 className="mt-6 text-4xl font-extrabold leading-[1.08] text-fg sm:text-5xl xl:text-6xl">
                Meça a qualidade do seu código com a{' '}
                <span className="bg-gradient-to-r from-brand-300 via-brand-400 to-cyan-300 bg-clip-text text-transparent">
                  precisão da indústria
                </span>
                .
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-relaxed text-fg-muted">
                O SoftMeter analisa repositórios do GitHub e transforma métricas de engenharia em
                indicadores claros de conformidade — com histórico, tendências e relatórios.
              </p>

              <div className="mt-8 flex flex-wrap gap-3">
                {isAuthenticated ? (
                  <Link to="/repositories" className={PRIMARY_LINK}>
                    Ir para a plataforma
                    <ArrowRightIcon className="h-4 w-4" />
                  </Link>
                ) : (
                  <>
                    <Link to="/register" className={PRIMARY_LINK}>
                      Começar agora
                      <ArrowRightIcon className="h-4 w-4" />
                    </Link>
                    <Link to="/login" className={SECONDARY_LINK}>
                      Já tenho conta
                    </Link>
                  </>
                )}
                <a href="#tutorial" className={`${SECONDARY_LINK} border-transparent bg-transparent`}>
                  Ver o tutorial
                </a>
              </div>

              <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-fg-muted">
                {['Python, JavaScript e TypeScript', 'Sem executar o seu código', '6 métricas de qualidade'].map((item) => (
                  <li key={item} className="inline-flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-conforme" aria-hidden="true" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            <div
              className="relative max-h-[30rem] animate-fade-up overflow-hidden [animation-delay:150ms] [mask-image:linear-gradient(to_bottom,black_72%,transparent)] lg:[transform:perspective(1800px)_rotateY(-7deg)_rotateX(2deg)]"
            >
              <BrowserFrame
                image={SCREENS.dashboard}
                alt="Dashboard de conformidade do SoftMeter com seis medidores de métricas"
                url="softmeter.app/dashboard"
                eager
              />
            </div>
          </div>
        </div>

        {/* ── O que é ────────────────────────────────────────── */}
        <Section id="o-que-e">
          <Reveal>
            <SectionHeading
              eyebrow="O que é o SoftMeter"
              title="Metrologia, agora para o software"
              text="Na indústria, uma peça é medida por um instrumento, comparada a uma tolerância e declarada conforme ou não. O SoftMeter aplica exatamente essa lógica ao código-fonte."
            />
          </Reveal>
          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {ANALOGY.map((item, index) => (
              <Reveal key={item.to} delay={index * 100}>
                <div className="h-full rounded-2xl border border-line bg-gradient-to-b from-surface to-surface/70 p-6 shadow-card">
                  <p className="text-xs font-medium uppercase tracking-wider text-fg-subtle">Na indústria</p>
                  <p className="mt-1 text-sm font-semibold text-fg-soft">{item.from}</p>
                  <div className="my-4 flex items-center gap-3" aria-hidden="true">
                    <span className="h-px flex-1 bg-gradient-to-r from-transparent to-brand-400/60" />
                    <ArrowRightIcon className="h-4 w-4 text-brand-400" />
                  </div>
                  <p className="text-xs font-medium uppercase tracking-wider text-brand-400">No SoftMeter</p>
                  <p className="mt-1 text-lg font-bold text-fg">{item.to}</p>
                  <p className="mt-3 text-sm leading-relaxed text-fg-muted">{item.text}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </Section>

        {/* ── Como funciona ──────────────────────────────────── */}
        <Section id="como-funciona">
          <Reveal>
            <SectionHeading
              eyebrow="Como funciona"
              title="Do repositório ao relatório em quatro etapas"
              text="Você só precisa da URL de um repositório público. O resto é automático."
            />
          </Reveal>
          <ol className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {JOURNEY.map((step, index) => (
              <li key={step.title}>
                <Reveal delay={index * 100} className="h-full">
                  <div className="relative h-full rounded-2xl border border-brand-500/30 bg-gradient-to-b from-surface to-canvas/60 p-6 shadow-neon">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-800 text-lg font-extrabold text-white shadow-brand">
                      {index + 1}
                    </span>
                    <h3 className="mt-5 text-lg font-bold text-fg">{step.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-fg-muted">{step.text}</p>
                  </div>
                </Reveal>
              </li>
            ))}
          </ol>
        </Section>

        {/* ── Métricas ───────────────────────────────────────── */}
        <Section id="metricas">
          <Reveal>
            <SectionHeading
              eyebrow="As métricas"
              title="Seis indicadores de qualidade, cada um com sua régua"
              text="Cada barra mostra as faixas de conformidade da métrica: verde para Conforme, âmbar para Condicional e vermelho para Não-Conforme."
            />
          </Reveal>
          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {METRICS_GAUGE_CONFIG.map((config, index) => {
              const info = METRIC_INFO[config.chave];
              return (
                <Reveal key={config.chave} delay={(index % 3) * 100}>
                  <article className="h-full rounded-2xl border border-line bg-gradient-to-b from-surface to-surface/70 p-6 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-400/50 hover:shadow-card-hover">
                    <h3 className="text-lg font-bold text-fg">{config.label}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-fg-soft">{info?.summary}</p>
                    <p className="mt-1.5 text-sm leading-relaxed text-fg-muted">{info?.reading}</p>
                    <div className="mt-5">
                      <BandBar config={config} />
                    </div>
                  </article>
                </Reveal>
              );
            })}
          </div>
        </Section>

        {/* ── Diferenciais ───────────────────────────────────── */}
        <Section id="diferenciais">
          <Reveal>
            <SectionHeading eyebrow="Por que o SoftMeter" title="Medição confiável, sem fricção" />
          </Reveal>
          <div className="mt-12 grid gap-5 sm:grid-cols-2">
            {DIFFERENTIALS.map((item, index) => {
              const Icon = DIFFERENTIAL_ICONS[index];
              return (
                <Reveal key={item.title} delay={(index % 2) * 100}>
                  <div className="flex h-full gap-5 rounded-2xl border border-line bg-gradient-to-b from-surface to-surface/70 p-6 shadow-card">
                    <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-500/15 text-brand-300 ring-1 ring-inset ring-brand-400/30">
                      <Icon className="h-6 w-6" />
                    </span>
                    <div>
                      <h3 className="text-lg font-bold text-fg">{item.title}</h3>
                      <p className="mt-1.5 text-sm leading-relaxed text-fg-muted">{item.text}</p>
                    </div>
                  </div>
                </Reveal>
              );
            })}
          </div>
        </Section>

        {/* ── Tutorial ───────────────────────────────────────── */}
        <Section id="tutorial">
          <Reveal>
            <SectionHeading
              eyebrow="Tutorial"
              title="Passo a passo: como usar o SoftMeter"
              text="Navegue pelos slides com os botões, os indicadores ou as setas do teclado."
            />
          </Reveal>
          <Reveal className="mt-12" delay={100}>
            <TutorialCarousel slides={TUTORIAL} />
          </Reveal>
        </Section>

        {/* ── FAQ ────────────────────────────────────────────── */}
        <Section id="faq">
          <Reveal>
            <SectionHeading eyebrow="Perguntas frequentes" title="Tire suas dúvidas" />
          </Reveal>
          <div className="mx-auto mt-12 flex max-w-3xl flex-col gap-3">
            {FAQ.map((item, index) => (
              <Reveal key={item.q} delay={index * 60}>
                <details className="group rounded-2xl border border-line bg-gradient-to-b from-surface to-surface/70 shadow-card open:border-brand-400/40">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 rounded-2xl px-5 py-4 text-left text-base font-semibold text-fg [&::-webkit-details-marker]:hidden">
                    {item.q}
                    <span
                      aria-hidden="true"
                      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white/5 text-lg leading-none text-brand-300 transition-transform duration-200 group-open:rotate-45"
                    >
                      +
                    </span>
                  </summary>
                  <p className="px-5 pb-5 text-sm leading-relaxed text-fg-muted">{item.a}</p>
                </details>
              </Reveal>
            ))}
          </div>
        </Section>

        {/* ── Chamada final ──────────────────────────────────── */}
        <section className="mx-auto w-full max-w-6xl px-4 pb-24 sm:px-6">
          <Reveal>
            <div className="relative overflow-hidden rounded-3xl border border-brand-400/30 bg-gradient-to-br from-ink-950 via-brand-900 to-brand-700 px-6 py-14 text-center shadow-neon sm:px-12">
              <div className="bg-grid pointer-events-none absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,black_20%,transparent_75%)]" />
              <div className="relative">
                <h2 className="text-3xl font-extrabold text-white sm:text-4xl">Pronto para medir o seu código?</h2>
                <p className="mx-auto mt-4 max-w-xl text-base text-brand-100">
                  Crie sua conta, cadastre um repositório e veja o primeiro dashboard em instantes.
                </p>
                <div className="mt-8 flex flex-wrap justify-center gap-3">
                  {isAuthenticated ? (
                    <Link
                      to="/repositories"
                      className="inline-flex min-h-[44px] items-center gap-2 rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-brand-800 transition-colors hover:bg-brand-100"
                    >
                      Ir para a plataforma
                      <ArrowRightIcon className="h-4 w-4" />
                    </Link>
                  ) : (
                    <>
                      <Link
                        to="/register"
                        className="inline-flex min-h-[44px] items-center gap-2 rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-brand-800 transition-colors hover:bg-brand-100"
                      >
                        Criar conta
                        <ArrowRightIcon className="h-4 w-4" />
                      </Link>
                      <Link
                        to="/login"
                        className="inline-flex min-h-[44px] items-center rounded-lg border border-white/30 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-white/10"
                      >
                        Entrar
                      </Link>
                    </>
                  )}
                </div>
              </div>
            </div>
          </Reveal>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 py-8 text-sm text-fg-muted sm:flex-row sm:px-6">
          <div className="flex flex-col items-center gap-2 sm:items-start">
            <Logo tone="light" />
            <p className="text-xs text-fg-subtle">Projeto de TCC · Metrologia aplicada à qualidade de software</p>
          </div>
          <a
            href={REPO_URL}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-lg px-3 py-2 transition-colors hover:bg-white/5 hover:text-fg"
          >
            <GithubIcon className="h-4 w-4" />
            Código no GitHub
          </a>
        </div>
      </footer>
    </div>
  );
}

export default HomePage;
