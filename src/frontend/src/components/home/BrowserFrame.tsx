import { Screenshot } from './content';

interface BrowserFrameProps {
  image: Screenshot;
  alt: string;
  /** Texto exibido na barra de endereço da moldura. */
  url?: string;
  /** Imagens abaixo da dobra carregam sob demanda. */
  eager?: boolean;
  /** Proporção fixa da área da imagem (ex.: '16 / 10'); sem ela, a imagem usa a altura natural. */
  ratio?: string;
  /** Com `ratio`: 'top' corta pela base; 'center' mostra a imagem inteira, centralizada. */
  fit?: 'top' | 'center';
  className?: string;
}

/** Moldura de janela de navegador ao redor de uma captura real da aplicação. */
function BrowserFrame({
  image,
  alt,
  url = 'softmeter.app',
  eager = false,
  ratio,
  fit = 'top',
  className = '',
}: BrowserFrameProps) {
  const imgClass = ratio
    ? `h-full w-full ${fit === 'top' ? 'object-cover object-top' : 'object-contain object-center'}`
    : 'h-auto w-full';
  return (
    <figure
      className={`overflow-hidden rounded-2xl border border-brand-500/40 bg-surface shadow-neon ${className}`}
    >
      <div className="flex items-center gap-3 border-b border-line bg-canvas/80 px-4 py-2.5" aria-hidden="true">
        <span className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-red-400/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-400/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-green-400/70" />
        </span>
        <span className="mx-auto w-full max-w-xs truncate rounded-md bg-white/5 px-3 py-1 text-center text-[11px] text-fg-subtle">
          {url}
        </span>
        <span className="w-12" />
      </div>
      <div style={ratio ? { aspectRatio: ratio } : undefined} className="bg-canvas">
        <img
          src={image.src}
          alt={alt}
          width={image.width}
          height={image.height}
          loading={eager ? 'eager' : 'lazy'}
          decoding="async"
          className={`block ${imgClass}`}
        />
      </div>
    </figure>
  );
}

export default BrowserFrame;
