/**
 * Message List Component - Displays chat messages
 * 
 * TODO: Implement this component to display the list of chat messages
 * with proper styling and message type handling.
 */

import React from 'react';
import { Message } from '../hooks/useSSEConnection';
import FunctionCallRenderer from './FunctionCallRenderer';

interface MessageListProps {
  messages: Message[];
  onInteraction?: (action: string, data: any) => void;
}

const MessageList: React.FC<MessageListProps> = ({ messages, onInteraction }) => {
  const bubbleStyles = (type: Message['type']) => {
    switch (type) {
      case 'user':
        return 'bg-blue-600 text-white self-end';
      case 'error':
        return 'error-message';
      case 'function_call':
        return '';
      default:
        return 'bg-gray-100';
    }
  };

  const avatar = (type: Message['type']) => {
    switch (type) {
      case 'user':
        return 'U';
      case 'error':
        return '!';
      default:
        return 'AI';
    }
  };

  // Hide transient first-turn send errors to avoid confusing the user
  const visibleMessages = messages.filter(m => !(m.type === 'error' && typeof m.content === 'string' && m.content.toLowerCase().includes('message send failed')));

  return (
    <div className="space-y-4">
      {visibleMessages.map((message) => (
        <div key={message.id} className="flex items-start space-x-3">
          <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
            <span className="text-xs">{avatar(message.type)}</span>
          </div>
          <div className="flex-1">
          <div className={`${message.type === 'function_call' ? '' : 'rounded-lg px-3 py-2'} ${bubbleStyles(message.type)}`}>
            {message.type === 'function_call' && message.function_call ? (
              <div>
                {(() => {
                  const fname = (message.function_call!.name || '').trim();
                  const hideBanner = fname === 'get_cart' || fname === 'remove_from_cart' || fname === 'update_cart' || fname === 'add_to_cart';
                  return hideBanner ? null : (
                    <div className="text-xs text-gray-500 mb-2">Function: {fname}</div>
                  );
                })()}
                <FunctionCallRenderer
                  functionCall={message.function_call}
                  onInteraction={(action, data) => {
                    onInteraction?.(action, data);
                  }}
                />
              </div>
            ) : (
              <p className="whitespace-pre-wrap break-words">{message.content}</p>
            )}
          </div>
            <div className="text-xs text-gray-500 mt-1">
              {message.timestamp.toLocaleTimeString()}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default MessageList;
