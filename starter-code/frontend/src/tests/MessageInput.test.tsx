import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import MessageInput from '../components/MessageInput';

describe('MessageInput Component', () => {
  test('renders input and send button', () => {
    const mockOnChange = jest.fn();
    const mockOnSend = jest.fn();

    render(
      <MessageInput
        value=""
        onChange={mockOnChange}
        onSend={mockOnSend}
        disabled={false}
        placeholder="Type message..."
      />
    );

    expect(screen.getByPlaceholderText(/type message/i)).toBeInTheDocument();
    expect(screen.getByText(/send/i)).toBeInTheDocument();
  });

  test('calls onChange when typing', () => {
    const mockOnChange = jest.fn();
    const mockOnSend = jest.fn();

    render(
      <MessageInput
        value=""
        onChange={mockOnChange}
        onSend={mockOnSend}
        disabled={false}
      />
    );

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'Hello' } });

    expect(mockOnChange).toHaveBeenCalledWith('Hello');
  });

  test('calls onSend when button clicked with non-empty value', () => {
    const mockOnChange = jest.fn();
    const mockOnSend = jest.fn();

    render(
      <MessageInput
        value="Test message"
        onChange={mockOnChange}
        onSend={mockOnSend}
        disabled={false}
      />
    );

    const sendButton = screen.getByText(/send/i);
    fireEvent.click(sendButton);

    expect(mockOnSend).toHaveBeenCalledWith('Test message');
  });

  test('disables controls when disabled prop is true', () => {
    const mockOnChange = jest.fn();
    const mockOnSend = jest.fn();

    render(
      <MessageInput
        value=""
        onChange={mockOnChange}
        onSend={mockOnSend}
        disabled={true}
      />
    );

    const input = screen.getByRole('textbox');
    const button = screen.getByText(/send/i);

    expect(input).toBeDisabled();
    expect(button).toBeDisabled();
  });

  test('does not call onSend with empty value', () => {
    const mockOnChange = jest.fn();
    const mockOnSend = jest.fn();

    render(
      <MessageInput
        value=""
        onChange={mockOnChange}
        onSend={mockOnSend}
        disabled={false}
      />
    );

    const sendButton = screen.getByText(/send/i);
    fireEvent.click(sendButton);

    expect(mockOnSend).not.toHaveBeenCalled();
  });
});