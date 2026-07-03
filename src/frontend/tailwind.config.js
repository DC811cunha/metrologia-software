/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        conforme: { DEFAULT: '#16a34a', bg: '#dcfce7', text: '#166534' },
        condicional: { DEFAULT: '#d97706', bg: '#fef3c7', text: '#92400e' },
        'nao-conforme': { DEFAULT: '#dc2626', bg: '#fee2e2', text: '#991b1b' },
        'nao-disponivel': { DEFAULT: '#6b7280', bg: '#f3f4f6', text: '#374151' },
      },
    },
  },
  plugins: [],
};
