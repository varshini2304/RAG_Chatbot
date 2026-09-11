import '@testing-library/jest-dom';
import { beforeAll, afterEach, afterAll } from 'vitest';
import { server } from './mocks/server';

// Start MSW server before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));

// Reset handlers after each test for test isolation
afterEach(() => {
  server.resetHandlers();
  localStorage.clear();
});

// Clean up after all tests complete
afterAll(() => server.close());

// Polyfill window.matchMedia for components using media queries or theme detection
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// Filter out Recharts container size warnings in JSDOM
const originalWarn = console.warn;
console.warn = (...args: unknown[]) => {
  if (typeof args[0] === 'string' && args[0].includes('The width(0) and height(0) of chart should be greater than 0')) {
    return;
  }
  originalWarn(...args);
};

// Polyfill ResizeObserver for Recharts / chart components
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
