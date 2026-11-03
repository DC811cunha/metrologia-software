import { KeyboardEvent, useRef, useState } from 'react';

import { ArrowLeftIcon, ArrowRightIcon } from '../ui/Icon';
import BrowserFrame from './BrowserFrame';
import { TutorialSlide } from './content';

interface TutorialCarouselProps {
  slides: TutorialSlide[];
}

const SWIPE_THRESHOLD_PX = 50;

const NAV_BUTTON_CLASSES =
  'flex h-11 w-11 items-center justify-center rounded-full border border-line-strong text-fg-soft transition-colors hover:border-brand-400/60 hover:bg-brand-500/10 hover:text-fg';

/**
 * Carrossel de tutorial. Sem rotação automática (WCAG 2.2.2), com botões, indicadores,
 * setas do teclado e gesto de arrastar; o slide atual é anunciado a leitores de tela.
 */
function TutorialCarousel({ slides }: TutorialCarouselProps) {
  const [index, setIndex] = useState(0);
  const touchStartX = useRef<number | null>(null);
  const total = slides.length;

  const goTo = (next: number) => setIndex((next + total) % total);

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      goTo(index + 1);
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault();
      goTo(index - 1);
    }
  }

  function handleTouchEnd(clientX: number) {
    if (touchStartX.current === null) return;
    const delta = clientX - touchStartX.current;
    touchStartX.current = null;
    if (Math.abs(delta) >= SWIPE_THRESHOLD_PX) goTo(index + (delta < 0 ? 1 : -1));
  }

  return (
    <div
      role="region"
      aria-roledescription="carrossel"
      aria-label="Tutorial passo a passo"
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onTouchStart={(event) => {
        touchStartX.current = event.touches[0].clientX;
      }}
      onTouchEnd={(event) => handleTouchEnd(event.changedTouches[0].clientX)}
      className="rounded-3xl outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-4 focus-visible:ring-offset-canvas"
    >
      <div className="overflow-hidden">
        <div
          className="flex transition-transform duration-500 ease-out"
          style={{ transform: `translateX(-${index * 100}%)` }}
          aria-live="polite"
        >
          {slides.map((slide, slideIndex) => (
            <div
              key={slide.title}
              role="group"
              aria-roledescription="slide"
              aria-label={`${slideIndex + 1} de ${total}`}
              aria-hidden={slideIndex !== index}
              className="grid w-full shrink-0 grid-cols-1 content-start items-center gap-8 px-1 py-2 lg:grid-cols-[0.8fr_1.2fr] lg:gap-12"
            >
              <div className="order-2 lg:order-1">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500/15 text-lg font-extrabold text-brand-300 ring-1 ring-inset ring-brand-400/30">
                  {slideIndex + 1}
                </span>
                <h3 className="mt-4 text-2xl font-extrabold text-fg">{slide.title}</h3>
                <p className="mt-3 text-base leading-relaxed text-fg-muted">{slide.text}</p>
              </div>
              <div className="order-1 lg:order-2">
                <BrowserFrame image={slide.image} alt={slide.alt} ratio="16 / 10" fit={slide.fit} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-8 flex items-center justify-between gap-4">
        <button type="button" onClick={() => goTo(index - 1)} aria-label="Passo anterior" className={NAV_BUTTON_CLASSES}>
          <ArrowLeftIcon className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-2" role="group" aria-label="Escolher passo">
          {slides.map((slide, slideIndex) => (
            <button
              key={slide.title}
              type="button"
              onClick={() => goTo(slideIndex)}
              aria-label={`Ir para o passo ${slideIndex + 1}: ${slide.title}`}
              aria-current={slideIndex === index ? 'step' : undefined}
              className="flex h-6 items-center px-0.5"
            >
              <span
                className={`block h-2 rounded-full transition-all duration-300 ${
                  slideIndex === index ? 'w-8 bg-brand-400 shadow-[0_0_10px_rgb(56_140_255/0.8)]' : 'w-2 bg-line-strong'
                }`}
              />
            </button>
          ))}
        </div>

        <button type="button" onClick={() => goTo(index + 1)} aria-label="Próximo passo" className={NAV_BUTTON_CLASSES}>
          <ArrowRightIcon className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}

export default TutorialCarousel;
