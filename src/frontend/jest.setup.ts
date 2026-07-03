import '@testing-library/jest-dom';

// jsdom não implementa ResizeObserver; Recharts (ResponsiveContainer) depende dele.
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = ResizeObserverMock;
