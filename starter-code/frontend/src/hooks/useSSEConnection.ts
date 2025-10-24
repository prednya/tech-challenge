/**
 * Custom hook for managing Server-Sent Events (SSE) connection
 * 
 * This hook provides:
 * - Real-time SSE connection management
 * - Message parsing and state management
 * - Auto-reconnection with exponential backoff
 * - Function call event handling
 * - Error handling and recovery
 */

import { useState, useEffect, useRef, useCallback } from 'react';

export interface Message {
  id: string;
  type: 'user' | 'assistant' | 'function_call' | 'error';
  content: string;
  timestamp: Date;
  function_call?: {
    name: string;
    parameters: Record<string, any>;
    result?: any;
  };
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface SSEConnectionOptions {
  sessionId: string;
  onMessage?: (message: Message) => void;
  onFunctionCall?: (functionCall: any) => void;
  onError?: (error: string) => void;
  maxReconnectAttempts?: number;
  baseReconnectDelay?: number;
}

export interface SSEConnectionHook {
  messages: Message[];
  connectionStatus: ConnectionStatus;
  sendMessage: (message: string, context?: Record<string, any>) => Promise<void>;
  clearMessages: () => void;
  reconnect: () => void;
  stop: () => void;
  error: string | null;
  isTyping: boolean;
}

export const useSSEConnection = (options: SSEConnectionOptions): SSEConnectionHook => {
  const {
    sessionId,
    onMessage,
    onFunctionCall,
    onError,
    maxReconnectAttempts = 5,
    baseReconnectDelay = 1000,
  } = options;

  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [error, setError] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  
  // Refs for managing connection
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  // Stable refs to avoid reconnect loops from changing callbacks
  const onMessageRef = useRef<typeof onMessage>(onMessage);
  const onFunctionCallRef = useRef<typeof onFunctionCall>(onFunctionCall);
  const onErrorRef = useRef<typeof onError>(onError);

  useEffect(() => { onMessageRef.current = onMessage; }, [onMessage]);
  useEffect(() => { onFunctionCallRef.current = onFunctionCall; }, [onFunctionCall]);
  useEffect(() => { onErrorRef.current = onError; }, [onError]);

  // Base API URL. Prefer relative paths in production behind the frontend proxy.
  const API_URL = process.env.REACT_APP_API_URL || '';

  const buildUrl = (path: string) => {
    // If API_URL provided, use it; otherwise use relative path to avoid CORS
    if (API_URL) return `${API_URL}${path}`;
    return path;
  };

  /**
   * Add a message to the messages array
   */
  const addMessage = useCallback((message: Message) => {
    setMessages(prev => [...prev, message]);
    onMessageRef.current?.(message);
  }, []);

  /**
   * Connect to SSE stream
   */
  const connect = useCallback(() => {
    if (!sessionId) {
      // Don't attempt to connect without a valid session
      return;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setConnectionStatus('connecting');
    setError(null);

    try {
      const eventSource = new EventSource(buildUrl(`/api/stream/${sessionId}`));
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('SSE connection opened');
        setConnectionStatus('connected');
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('SSE message received:', data);
          
          // Handle different event types
          handleSSEEvent(data, event.type || 'message');
        } catch (err) {
          console.error('Failed to parse SSE message:', err);
        }
      };

      // Handle specific event types
      eventSource.addEventListener('text_chunk', (event) => {
        const data = JSON.parse((event as MessageEvent).data);
        handleTextChunk(data);
      });

      eventSource.addEventListener('function_call', (event) => {
        const data = JSON.parse((event as MessageEvent).data);
        handleFunctionCall(data);
      });

      eventSource.addEventListener('completion', (event) => {
        const data = JSON.parse((event as MessageEvent).data);
        handleCompletion(data);
      });

      // Handle server-emitted error events (custom SSE event named "error")
      // Note: This may also receive network error Events without data
      eventSource.addEventListener('error', (event) => {
        try {
          const me = event as MessageEvent;
          if ((me as any).data) {
            const data = JSON.parse((me as any).data);
            handleErrorEvent(data);
          } else {
            // Network-level error without payload
            setConnectionStatus('error');
            if (reconnectAttemptsRef.current < maxReconnectAttempts) {
              scheduleReconnect();
            } else {
              setError('Max reconnection attempts reached');
              onErrorRef.current?.('Max reconnection attempts reached');
            }
          }
        } catch (e) {
          console.error('Failed to process error event', e);
        }
      });

      // Remove duplicate 'error' listeners; use unified handler above

      eventSource.onerror = (event) => {
        console.error('SSE error:', event);
        setConnectionStatus('error');
        
        // Attempt reconnection
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          scheduleReconnect();
        } else {
          setError('Max reconnection attempts reached');
          onError?.('Max reconnection attempts reached');
        }
      };

    } catch (err) {
      console.error('Failed to create SSE connection:', err);
      setConnectionStatus('error');
      setError('Failed to establish connection');
      onErrorRef.current?.('Failed to establish connection');
    }
  }, [sessionId, API_URL, maxReconnectAttempts, baseReconnectDelay]);

  /**
   * Handle generic SSE events
   */
  const handleSSEEvent = (data: any, eventType: string) => {
    switch (eventType) {
      case 'connection':
        console.log('Connection established:', data);
        break;
      default:
        console.log('Unknown event type:', eventType, data);
    }
  };

  /**
   * Handle text chunk streaming
   */
  const handleTextChunk = (data: any) => {
    const { content, partial } = data;
    
    if (partial) {
      // Update the last assistant message or create a new one
      setMessages(prev => {
        const lastMessage = prev[prev.length - 1];
        
        if (lastMessage && lastMessage.type === 'assistant') {
          // Append to existing message
          return prev.map((msg, index) => 
            index === prev.length - 1 
              ? { ...msg, content: msg.content + content }
              : msg
          );
        } else {
          // Create new assistant message
          return [...prev, {
            id: `msg_${Date.now()}`,
            type: 'assistant',
            content,
            timestamp: new Date()
          }];
        }
      });
    } else {
      // Complete message
      addMessage({
        id: `msg_${Date.now()}`,
        type: 'assistant',
        content,
        timestamp: new Date()
      });
    }

    setIsTyping(true);
  };

  /**
   * Handle function call events
   */
  const handleFunctionCall = (data: any) => {
    const { function: functionName, parameters, result } = data;
    
    const message: Message = {
      id: `func_${Date.now()}`,
      type: 'function_call',
      content: `Executing ${functionName}`,
      timestamp: new Date(),
      function_call: {
        name: functionName,
        parameters,
        result
      }
    };

    addMessage(message);
    onFunctionCallRef.current?.(data);
  };

  /**
   * Handle completion events
   */
  const handleCompletion = (data: any) => {
    console.log('Turn completed:', data);
    setIsTyping(false);
  };

  /**
   * Handle error events
   */
  const handleErrorEvent = (data: any) => {
    const errorMessage: Message = {
      id: `error_${Date.now()}`,
      type: 'error',
      content: data.error || 'An error occurred',
      timestamp: new Date()
    };

    addMessage(errorMessage);
    setError(data.error);
    onErrorRef.current?.(data.error);
  };

  /**
   * Schedule reconnection with exponential backoff
   */
  const scheduleReconnect = () => {
    const delay = baseReconnectDelay * Math.pow(2, reconnectAttemptsRef.current);
    
    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectAttemptsRef.current++;
      console.log(`Reconnection attempt ${reconnectAttemptsRef.current}`);
      connect();
    }, delay);
  };

  /**
   * Send a message to the backend
   */
  const sendMessage = async (message: string, context?: Record<string, any>) => {
    if (!abortControllerRef.current) {
      abortControllerRef.current = new AbortController();
    }

    try {
      // Add user message immediately
      addMessage({
        id: `user_${Date.now()}`,
        type: 'user',
        content: message,
        timestamp: new Date()
      });

      // Send message to backend
      const response = await fetch(buildUrl(`/api/chat/${sessionId}/message`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          context: context || {}
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('Message sent successfully:', result);

    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.warn('Send message failed (non-fatal):', err);
        // Show a lightweight inline error message but do not mark connection as errored
        addMessage({
          id: `send_error_${Date.now()}`,
          type: 'error',
          content: 'Message send failed, retry if needed',
          timestamp: new Date()
        });
      }
    }
  };

  /**
   * Clear all messages
   */
  const clearMessages = () => {
    setMessages([]);
  };

  /**
   * Manually trigger reconnection
   */
  const reconnect = () => {
    reconnectAttemptsRef.current = 0;
    connect();
  };

  /**
   * Disconnect and cleanup
   */
  const disconnect = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    setConnectionStatus('disconnected');
  };

  /**
   * Stop current streaming/generation by closing SSE and reconnecting fresh.
   */
  const stop = () => {
    disconnect();
    setIsTyping(false);
    setError(null);
    // Reconnect after a short delay to be ready for next turn
    setTimeout(() => {
      connect();
    }, 250);
  };

  // Auto-connect on mount
  useEffect(() => {
    if (!sessionId) return;
    if (!eventSourceRef.current) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [sessionId]);

  return {
    messages,
    connectionStatus,
    sendMessage,
    clearMessages,
    reconnect,
    stop,
    error,
    isTyping
  };
};
