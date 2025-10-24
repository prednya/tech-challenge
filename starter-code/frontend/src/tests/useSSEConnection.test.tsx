import { renderHook, act, waitFor } from '@testing-library/react';
import { useSSEConnection } from 'hooks/useSSEConnection';

// Fix TypeScript 'global' error
declare const global: any;

// Simple Mock EventSource
class MockEventSource {
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: any) => void) | null = null;
  onerror: (() => void) | null = null;
  readyState: number = 0;

  constructor(url: string) {
    this.url = url;
    setTimeout(() => {
      this.readyState = 1;
      if (this.onopen) {
        this.onopen();
      }
    }, 50);
  }

  addEventListener(event: string, handler: any) {
    if (event === 'open') this.onopen = handler;
    if (event === 'message') this.onmessage = handler;
    if (event === 'error') this.onerror = handler;
  }

  removeEventListener() {}

  close() {
    this.readyState = 2;
  }

  dispatchEvent() {
    return true;
  }
}

describe('useSSEConnection Hook', () => {
  let mockEventSource: MockEventSource;

  beforeEach(() => {
    // Suppress console logs in tests
    jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'warn').mockImplementation(() => {});

    // Mock fetch
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      } as Response)
    );

    // Mock EventSource
    global.EventSource = jest.fn((url: string) => {
      mockEventSource = new MockEventSource(url);
      return mockEventSource;
    }) as any;
  });

  afterEach(() => {
    jest.clearAllMocks();
    jest.restoreAllMocks();
  });

  test('initializes with empty messages', () => {
    const { result } = renderHook(() =>
      useSSEConnection({ sessionId: 'test-123' })
    );

    expect(result.current.messages).toEqual([]);
  });

  test('has sendMessage function', () => {
    const { result } = renderHook(() =>
      useSSEConnection({ sessionId: 'test-123' })
    );

    expect(typeof result.current.sendMessage).toBe('function');
  });

  test('has clearMessages function', () => {
    const { result } = renderHook(() =>
      useSSEConnection({ sessionId: 'test-123' })
    );

    expect(typeof result.current.clearMessages).toBe('function');
  });

  test('has connectionStatus', () => {
    const { result } = renderHook(() =>
      useSSEConnection({ sessionId: 'test-123' })
    );

    expect(result.current.connectionStatus).toBeDefined();
  });

  test('creates EventSource on mount', async () => {
    renderHook(() =>
      useSSEConnection({ sessionId: 'test-123' })
    );

    await waitFor(() => {
      expect(global.EventSource).toHaveBeenCalled();
    });
  });

  test('sendMessage adds user message', async () => {
    const { result } = renderHook(() =>
      useSSEConnection({ sessionId: 'test-123' })
    );

    await act(async () => {
      await result.current.sendMessage('Hello');
    });

    await waitFor(() => {
      expect(result.current.messages.length).toBeGreaterThan(0);
    });

    const userMessage = result.current.messages.find(m => m.type === 'user');
    expect(userMessage).toBeDefined();
    expect(userMessage?.content).toBe('Hello');
  });

  test('sendMessage calls fetch', async () => {
    const { result } = renderHook(() =>
      useSSEConnection({ sessionId: 'test-123' })
    );

    await act(async () => {
      await result.current.sendMessage('Test message');
    });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });
  });

  test('clearMessages empties message array', async () => {
    const { result } = renderHook(() =>
      useSSEConnection({ sessionId: 'test-123' })
    );

    // Add a message first
    await act(async () => {
      await result.current.sendMessage('Test');
    });

    await waitFor(() => {
      expect(result.current.messages.length).toBeGreaterThan(0);
    });

    // Clear messages
    act(() => {
      result.current.clearMessages();
    });

    expect(result.current.messages).toEqual([]);
  });

  test('handles multiple messages', async () => {
    const { result } = renderHook(() =>
      useSSEConnection({ sessionId: 'test-123' })
    );

    await act(async () => {
      await result.current.sendMessage('First');
      await result.current.sendMessage('Second');
    });

    await waitFor(() => {
      expect(result.current.messages.length).toBeGreaterThanOrEqual(2);
    });
  });

  test('closes EventSource on unmount', async () => {
    const { unmount } = renderHook(() =>
      useSSEConnection({ sessionId: 'test-123' })
    );

    await waitFor(() => {
      expect(mockEventSource).toBeDefined();
    });

    const closeSpy = jest.spyOn(mockEventSource, 'close');

    unmount();

    expect(closeSpy).toHaveBeenCalled();
  });

  test('handles fetch errors gracefully', async () => {
    global.fetch = jest.fn(() =>
      Promise.reject(new Error('Network error'))
    );

    const { result } = renderHook(() =>
      useSSEConnection({ sessionId: 'test-123' })
    );

    await act(async () => {
      await result.current.sendMessage('Test');
    });

    // Should not crash - hook handles error internally
    expect(result.current.messages).toBeDefined();
  });

  test('connection status is defined', async () => {
    const { result } = renderHook(() =>
      useSSEConnection({ sessionId: 'test-123' })
    );

    await waitFor(() => {
      expect(result.current.connectionStatus).toBeDefined();
    });
  });

  test('messages array is always an array', () => {
    const { result } = renderHook(() =>
      useSSEConnection({ sessionId: 'test-123' })
    );

    expect(Array.isArray(result.current.messages)).toBe(true);
  });

  test('sendMessage returns without throwing', async () => {
    const { result } = renderHook(() =>
      useSSEConnection({ sessionId: 'test-123' })
    );

    await expect(
      act(async () => {
        await result.current.sendMessage('Test');
      })
    ).resolves.not.toThrow();
  });

  test('clearMessages returns without throwing', () => {
    const { result } = renderHook(() =>
      useSSEConnection({ sessionId: 'test-123' })
    );

    expect(() => {
      act(() => {
        result.current.clearMessages();
      });
    }).not.toThrow();
  });
});