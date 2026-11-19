// Configuração do ESLint 9 (formato "flat"). Equivale ao antigo .eslintrc.cjs:
// eslint:recommended + @typescript-eslint/recommended + react-hooks/recommended, ambiente de navegador,
// diretórios gerados ignorados e `no-unused-vars` como aviso.
const js = require('@eslint/js');
const { defineConfig, globalIgnores } = require('eslint/config');
const globals = require('globals');
const reactHooks = require('eslint-plugin-react-hooks');
const tseslint = require('typescript-eslint');

module.exports = defineConfig([
  globalIgnores(['dist', 'node_modules', 'coverage']),
  js.configs.recommended,
  tseslint.configs.recommended,
  reactHooks.configs.flat.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: globals.browser,
    },
    rules: {
      '@typescript-eslint/no-unused-vars': 'warn',
    },
  },
]);
