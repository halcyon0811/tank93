import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['tests/unit.test.js'],
    environment: 'node',
    globals: false,
    testTimeout: 10000,
  },
});
