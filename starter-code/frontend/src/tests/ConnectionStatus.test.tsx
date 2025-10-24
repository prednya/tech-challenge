import React from 'react';
import { render, screen } from '@testing-library/react';
import ConnectionStatus from '../components/ConnectionStatus';

describe('ConnectionStatus Component', () => {
  test('displays connecting status', () => {
    render(<ConnectionStatus status="connecting" />);
    expect(screen.getByText(/connecting/i)).toBeInTheDocument();
  });

  test('displays connected status', () => {
    render(<ConnectionStatus status="connected" />);
    expect(screen.getByText(/connected/i)).toBeInTheDocument();
  });

  test('displays disconnected status', () => {
    render(<ConnectionStatus status="disconnected" />);
    expect(screen.getByText(/disconnected/i)).toBeInTheDocument();
  });

  test('displays error status', () => {
    render(<ConnectionStatus status="error" />);
    expect(screen.getByText(/error/i)).toBeInTheDocument();
  });
});