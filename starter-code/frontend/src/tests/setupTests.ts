import '@testing-library/jest-dom';

// Mock EventSource for SSE
class MockEventSource {
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  readyState: number = 0;

  constructor(url: string) {
    this.url = url;
  }

  addEventListener() {}
  removeEventListener() {}
  close() {
    this.readyState = 2;
  }
  dispatchEvent() {
    return true;
  }
}

(global as any).EventSource = MockEventSource;

// Mock fetch
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ success: true }),
  } as Response)
);