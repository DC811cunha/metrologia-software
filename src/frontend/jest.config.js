/** @type {import('jest').Config} */
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  testPathIgnorePatterns: ['/node_modules/', '/tests/e2e/'],
  // Services make HTTP calls and are mocked in unit tests; they are covered by
  // backend integration tests. Excluding them keeps the threshold meaningful.
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/main.tsx',
    '!src/vite-env.d.ts',
    '!src/services/**',
  ],
  coverageThreshold: {
    global: {
      statements: 80,
      lines: 80,
      functions: 75,
      branches: 70,
    },
  },
};
