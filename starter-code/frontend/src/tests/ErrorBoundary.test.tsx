import React from 'react';
import { render, screen } from '@testing-library/react';
import ErrorBoundary from '../components/ErrorBoundary';

const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div>Component rendered successfully</div>;
};

describe('ErrorBoundary Component', () => {
  const originalError = console.error;
  
  beforeEach(() => {
    console.error = jest.fn();
  });

  afterEach(() => {
    console.error = originalError;
  });

  test('renders children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Component rendered successfully')).toBeInTheDocument();
  });

  test('renders error UI when child component throws', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });
});