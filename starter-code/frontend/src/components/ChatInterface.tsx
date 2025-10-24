/**
 * Main chat interface component for the AI Product Discovery Assistant.
 * 
 * This component provides:
 * - Real-time chat with SSE connection
 * - Dynamic component rendering for function calls
 * - Message history and typing indicators
 * - Error handling and recovery
 */

import React, { useState, useEffect, useRef } from 'react';
import { useSSEConnection } from '../hooks/useSSEConnection';
import { useAppState } from '../context/AppStateContext';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import ConnectionStatus from './ConnectionStatus';

const ChatInterface: React.FC = () => {
  const { sessionId, createSession } = useAppState();
  const [inputValue, setInputValue] = useState('');
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Initialize session if needed
  useEffect(() => {
    if (!sessionId) {
      // Only depend on sessionId to avoid re-creating sessions due to function identity changes
      createSession();
    }
  }, [sessionId]);

  // SSE Connection
  const {
    messages,
    connectionStatus,
    sendMessage,
    clearMessages,
    reconnect,
    stop,
    error,
    isTyping
  } = useSSEConnection({
    sessionId: sessionId || '',
    onMessage: (message) => {
      console.log('New message:', message);
    },
    onFunctionCall: (functionCall) => {
      console.log('Function call:', functionCall);
    },
    onError: (error) => {
      console.error('SSE error:', error);
    }
  });

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSendMessage = async (message: string) => {
    if (message.trim() && sessionId) {
      try {
        try {
          await sendMessage(message.trim());
        } catch (e) {
          // Retry once after a short delay to avoid first-turn race conditions
          await new Promise(r => setTimeout(r, 250));
          await sendMessage(message.trim());
        }
        setInputValue('');
      } catch (err) {
        console.error('Failed to send message:', err);
      }
    }
  };

  const handleClearChat = () => {
    clearMessages();
  };

  if (!sessionId) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-500">Initializing session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden max-w-4xl mx-auto">
      {/* Header */}
      <div className="bg-gray-50 px-4 py-3 border-b flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <ConnectionStatus status={connectionStatus} />
          <span className="text-sm text-gray-600">
            Session: {sessionId.slice(0, 8)}...
          </span>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={stop}
            disabled={connectionStatus !== 'connected'}
            className="px-3 py-1 text-xs bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Stop
          </button>
          <button
            onClick={reconnect}
            disabled={connectionStatus === 'connected'}
            className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Reconnect
          </button>
          <button
            onClick={handleClearChat}
            className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">
                Connection Error: {error}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Chat Messages */}
      <div 
        ref={chatContainerRef}
        className="chat-container h-96 overflow-y-auto p-4 space-y-4"
      >
        {messages.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-gray-400 text-lg mb-2">👋</div>
            <p className="text-gray-500 mb-4">
              Hi! I'm your AI shopping assistant. I can help you:
            </p>
            <div className="text-sm text-gray-400 space-y-1">
              <p>• Search for products</p>
              <p>• Get detailed product information</p>
              <p>• Add items to your cart</p>
              <p>• Find recommendations</p>
            </div>
            <p className="text-gray-500 mt-4 text-sm">
              What would you like to find today?
            </p>
          </div>
        ) : (
          <MessageList
            messages={messages}
            onInteraction={(action, data) => {
              if (action === 'select_product' && data?.product_id) {
                sendMessage(`details ${data.product_id}`);
              } else if (action === 'add_to_cart' && data?.product_id) {
                const qty = data.quantity ?? 1;
                sendMessage(`add to cart ${data.product_id} ${qty}`);
              } else if (action === 'remove_from_cart') {
                // Call REST endpoint directly, then refresh cart view silently
                const payload: any = { session_id: sessionId };
                if (data?.product_id) payload.product_id = data.product_id;
                if (data?.item_id) payload.item_id = data.item_id;
                fetch(`/api/functions/remove_from_cart`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(payload),
                }).finally(() => {
                  // Show updated cart (silent function_call in SSE)
                  sendMessage('show cart');
                });
              } else if (action === 'update_cart' && data?.product_id && typeof data?.delta === 'number') {
                // Call REST endpoint directly, then refresh cart view silently
                const body = { session_id: sessionId, product_id: data.product_id, delta: data.delta };
                fetch(`/api/functions/update_cart`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(body),
                }).finally(() => {
                  sendMessage('show cart');
                });
              }
            }}
          />
        )}

        {/* Typing Indicator */}
        {isTyping && (
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-blue-600 text-xs">AI</span>
            </div>
            <div className="bg-gray-100 rounded-lg px-4 py-2">
              <div className="typing-indicator">
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Message Input */}
      <MessageInput
        value={inputValue}
        onChange={setInputValue}
        onSend={handleSendMessage}
        disabled={connectionStatus !== 'connected'}
        placeholder="Ask me about products, search for items, or get recommendations..."
      />
    </div>
  );
};

export default ChatInterface;
