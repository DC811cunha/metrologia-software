/** @type {import('jest').Config} */
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/tests'],
  collectCoverageFrom: [
    'src/services/**/*.ts',
    '!src/index.ts',
  ],
  testMatch: ['**/*.test.ts'],
};
