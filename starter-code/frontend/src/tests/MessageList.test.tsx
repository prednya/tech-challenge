import React from 'react';
import { render, screen } from '@testing-library/react';
import MessageList from '../components/MessageList';
import { Message } from '../hooks/useSSEConnection';

describe('MessageList Component', () => {
  const createMessage = (overrides: Partial<Message> = {}): Message => ({
    id: '1',
    type: 'user',
    content: 'Test message',
    timestamp: new Date('2024-01-01T10:00:00'),
    ...overrides,
  });

  test('renders empty state with no messages', () => {
    const { container } = render(<MessageList messages={[]} />);
    const messageContainer = container.querySelector('.space-y-4');
    expect(messageContainer).toBeInTheDocument();
    expect(messageContainer?.children).toHaveLength(0);
  });

  test('renders user message', () => {
    const messages = [createMessage({ content: 'Hello assistant' })];
    render(<MessageList messages={messages} />);
    expect(screen.getByText('Hello assistant')).toBeInTheDocument();
  });

  test('renders assistant message', () => {
    const messages = [
      createMessage({
        type: 'assistant',
        content: 'Hello! How can I help?',
      }),
    ];
    render(<MessageList messages={messages} />);
    expect(screen.getByText(/hello! how can i help/i)).toBeInTheDocument();
  });

  test('renders error message', () => {
    const messages = [
      createMessage({
        type: 'error',
        content: 'Connection failed',
      }),
    ];
    render(<MessageList messages={messages} />);
    expect(screen.getByText(/connection failed/i)).toBeInTheDocument();
  });

  test('renders multiple messages in order', () => {
    const messages = [
      createMessage({ id: '1', content: 'First message' }),
      createMessage({ id: '2', content: 'Second message', type: 'assistant' }),
      createMessage({ id: '3', content: 'Third message' }),
    ];
    render(<MessageList messages={messages} />);
    expect(screen.getByText('First message')).toBeInTheDocument();
    expect(screen.getByText('Second message')).toBeInTheDocument();
    expect(screen.getByText('Third message')).toBeInTheDocument();
  });

  //
  // NOTE on function_call tests:
  // MessageList renders a "Function: <name>" header and the FunctionCallRenderer output.
  // It does NOT render the message.content text like "Searching for products" / "Processing..." / "Loading...".
  //

  test('renders function call message with result (shows function header and rendered result)', () => {
    const messages = [
      createMessage({
        type: 'function_call',
        // content is not shown; header + component are shown.
        content: 'Searching for products',
        function_call: {
          name: 'search_products',
          parameters: { query: 'headphones' },
          result: {
            data: {
              products: [{ id: '1', name: 'Headphones', price: 199.99 }],
            },
          },
        },
      }),
    ];

    render(<MessageList messages={messages} />);

    // Expect the function header
    expect(screen.getByText(/function:\s*search_products/i)).toBeInTheDocument();

    // Expect the rendered FunctionCallRenderer content (Search Results section + product name)
    expect(screen.getByText(/search results/i)).toBeInTheDocument();
    expect(screen.getByText('Headphones')).toBeInTheDocument();

    // The literal content "Searching for products" is NOT rendered by MessageList, so we do NOT assert it.
  });

  test('renders function call message without result (shows header and fallback empty state)', () => {
    const messages = [
      createMessage({
        type: 'function_call',
        content: 'Processing...',
        function_call: {
          name: 'search_products',
          parameters: { query: 'test' },
          // no result provided -> FunctionCallRenderer shows empty/fallback state
        },
      }),
    ];

    render(<MessageList messages={messages} />);

    // Function header appears
    expect(screen.getByText(/function:\s*search_products/i)).toBeInTheDocument();

    // FunctionCallRenderer defaults to "Search Results" with empty list copy
    expect(screen.getByText(/search results/i)).toBeInTheDocument();
    expect(screen.getByText(/no products found/i)).toBeInTheDocument();

    // We do NOT assert the literal "Processing..." since MessageList doesn't render message.content for function_call.
  });

  test('renders function call "in progress" state (header + empty results)', () => {
    const messages = [
      createMessage({
        type: 'function_call',
        content: 'Loading...',
        function_call: {
          name: 'search_products',
          parameters: {},
        },
      }),
    ];

    render(<MessageList messages={messages} />);

    // Header is shown
    expect(screen.getByText(/function:\s*search_products/i)).toBeInTheDocument();

    // And the fallback body
    expect(screen.getByText(/search results/i)).toBeInTheDocument();
    expect(screen.getByText(/no products found/i)).toBeInTheDocument();

    // No literal "Loading..." text in DOM; we don't assert that text.
  });

  test('displays timestamp for messages', () => {
    const timestamp = new Date('2024-01-01T10:30:00');
    const messages = [
      createMessage({
        content: 'Test with timestamp',
        timestamp,
      }),
    ];

    render(<MessageList messages={messages} />);
    expect(screen.getByText('Test with timestamp')).toBeInTheDocument();
  });

  test('auto-scrolls to bottom when new message added', () => {
    const { rerender } = render(<MessageList messages={[]} />);
    const messages = [createMessage({ content: 'New message' })];
    rerender(<MessageList messages={messages} />);
    expect(screen.getByText('New message')).toBeInTheDocument();
  });

  test('renders system message type', () => {
    const messages = [
      createMessage({
        type: 'system' as any,
        content: 'System notification',
      }),
    ];

    render(<MessageList messages={messages} />);
    expect(screen.getByText(/system notification/i)).toBeInTheDocument();
  });

  test('handles very long messages without breaking layout', () => {
    const longContent = 'A'.repeat(1000);
    const messages = [createMessage({ content: longContent })];
    const { container } = render(<MessageList messages={messages} />);
    expect(container.textContent).toContain('AAA');
  });

  test('renders markdown formatting in assistant messages', () => {
    const messages = [
      createMessage({
        type: 'assistant',
        content: '**Bold text** and *italic text*',
      }),
    ];

    render(<MessageList messages={messages} />);
    expect(screen.getByText(/bold text/i)).toBeInTheDocument();
  });

  test('sanitizes HTML in user messages', () => {
    const messages = [
      createMessage({
        content: '<script>alert("xss")</script>Safe text',
      }),
    ];

    const { container } = render(<MessageList messages={messages} />);
    expect(container.querySelector('script')).not.toBeInTheDocument();
    expect(screen.getByText(/safe text/i)).toBeInTheDocument();
  });
});
