/** @type {import('tailwindcss').Config} */

// Tokens semânticos lidos de variáveis CSS (definidas em src/index.css) — o tema vive
// em um único lugar, e `<alpha-value>` mantém utilitários como `bg-surface/80` funcionando.
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
      },
      colors: {
        // Identidade da marca — azul (contraste AA com texto branco a partir de 600)
        brand: {
          50: '#eef5ff',
          100: '#d9e8ff',
          200: '#bcd8ff',
          300: '#8ebfff',
          400: '#589bff',
          500: '#3478f6',
          600: '#1f5ae0',
          700: '#1a47b8',
          800: '#1b3d94',
          900: '#1a3575',
          950: '#0f1f4a',
        },
        // Superfícies e texto do tema (valores em src/index.css)
        canvas: token('canvas'),
        surface: token('surface'),
        'surface-2': token('surface-2'),
        line: token('line'),
        'line-strong': token('line-strong'),
        field: token('field'),
        fg: token('fg'),
        'fg-soft': token('fg-soft'),
        'fg-muted': token('fg-muted'),
        'fg-subtle': token('fg-subtle'),
        glow: token('glow'),
        // Navy profundo para superfícies escuras (navbar, painéis de destaque)
        ink: {
          700: '#16275a',
          800: '#0f1d47',
          900: '#0a1433',
          950: '#060d24',
        },
        // Semântica de conformidade — mantida distinta do azul da marca
        conforme: { DEFAULT: '#22c55e', bg: 'rgb(34 197 94 / 0.14)', text: '#4ade80' },
        condicional: { DEFAULT: '#f59e0b', bg: 'rgb(245 158 11 / 0.14)', text: '#fbbf24' },
        'nao-conforme': { DEFAULT: '#ef4444', bg: 'rgb(239 68 68 / 0.14)', text: '#f87171' },
        'nao-disponivel': { DEFAULT: '#94a3b8', bg: 'rgb(148 163 184 / 0.14)', text: '#cbd5e1' },
      },
      boxShadow: {
        card: '0 1px 0 0 rgb(255 255 255 / 0.03) inset, 0 12px 32px -16px rgb(0 0 0 / 0.7)',
        // Borda luminosa azul — o traço de identidade dos cards de destaque
        neon: '0 0 0 1px rgb(var(--glow) / 0.45), 0 0 28px -6px rgb(var(--glow) / 0.35)',
        'neon-hover':
          '0 0 0 1px rgb(var(--glow) / 0.8), 0 0 40px -4px rgb(var(--glow) / 0.55)',
        'card-hover': '0 0 0 1px rgb(var(--glow) / 0.45), 0 16px 40px -12px rgb(var(--glow) / 0.35)',
        glow: '0 0 0 3px rgb(var(--glow) / 0.28)',
        brand: '0 8px 24px -6px rgb(31 90 224 / 0.6)',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        // O ponteiro varre de -90° até o valor real (definido inline pelo componente)
        'needle-sweep': {
          '0%': { transform: 'translateX(-50%) rotate(-90deg)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'pulse-ring': {
          '0%': { boxShadow: '0 0 0 0 rgba(88, 155, 255, 0.55)' },
          '100%': { boxShadow: '0 0 0 14px rgba(88, 155, 255, 0)' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.5s cubic-bezier(0.22, 1, 0.36, 1) both',
        'fade-in': 'fade-in 0.4s ease-out both',
        'needle-sweep': 'needle-sweep 1.1s cubic-bezier(0.34, 1.56, 0.64, 1) both',
        float: 'float 6s ease-in-out infinite',
        'pulse-ring': 'pulse-ring 1.8s ease-out infinite',
      },
    },
  },
  plugins: [],
};
