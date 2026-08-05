import '@testing-library/jest-dom/vitest'

class ResizeObserverStub implements ResizeObserver {
  constructor(callback: ResizeObserverCallback) {
    void callback
  }

  observe(): void {}

  unobserve(): void {}

  disconnect(): void {}
}

globalThis.ResizeObserver = ResizeObserverStub
