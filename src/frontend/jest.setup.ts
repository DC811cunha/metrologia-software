import { TextDecoder, TextEncoder } from 'util';

// react-router 7 usa TextEncoder/TextDecoder, que o jsdom não implementa.
Object.assign(globalThis, { TextEncoder, TextDecoder });

import '@testing-library/jest-dom';

// jsdom não implementa ResizeObserver; Recharts (ResponsiveContainer) depende dele.
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = ResizeObserverMock;
