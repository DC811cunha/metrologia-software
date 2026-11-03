/** @type {import('tailwindcss').Config} */
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
        // Navy profundo para superfícies escuras (navbar, painéis de destaque)
        ink: {
          700: '#16275a',
          800: '#0f1d47',
          900: '#0a1433',
          950: '#060d24',
        },
        // Semântica de conformidade — mantida distinta do azul da marca
        conforme: { DEFAULT: '#16a34a', bg: '#dcfce7', text: '#166534' },
        condicional: { DEFAULT: '#d97706', bg: '#fef3c7', text: '#92400e' },
        'nao-conforme': { DEFAULT: '#dc2626', bg: '#fee2e2', text: '#991b1b' },
        'nao-disponivel': { DEFAULT: '#6b7280', bg: '#f3f4f6', text: '#374151' },
      },
      boxShadow: {
        card: '0 1px 2px rgba(15, 29, 71, 0.04), 0 4px 16px -4px rgba(15, 29, 71, 0.08)',
        'card-hover': '0 2px 4px rgba(15, 29, 71, 0.06), 0 12px 32px -8px rgba(31, 90, 224, 0.22)',
        glow: '0 0 0 4px rgba(52, 120, 246, 0.18)',
        brand: '0 8px 24px -6px rgba(31, 90, 224, 0.55)',
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
