/**
 * Connection Status Component - Shows SSE connection status
 * 
 * TODO: Implement visual indicator for connection status
 */

import React from 'react';
import { ConnectionStatus as Status } from '../hooks/useSSEConnection';

interface ConnectionStatusProps {
  status: Status;
}

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ status }) => {
  const getStatusDisplay = () => {
    switch (status) {
      case 'connecting':
        return {
          color: 'text-yellow-600',
          bg: 'bg-yellow-100',
          text: 'Connecting...',
          icon: '⏳'
        };
      case 'connected':
        return {
          color: 'text-green-600',
          bg: 'bg-green-100',
          text: 'Connected',
          icon: '✅'
        };
      case 'disconnected':
        return {
          color: 'text-gray-600',
          bg: 'bg-gray-100',
          text: 'Disconnected',
          icon: '⭕'
        };
      case 'error':
        return {
          color: 'text-red-600',
          bg: 'bg-red-100',
          text: 'Connection Error',
          icon: '❌'
        };
      default:
        return {
          color: 'text-gray-600',
          bg: 'bg-gray-100',
          text: 'Unknown',
          icon: '❓'
        };
    }
  };

  const statusDisplay = getStatusDisplay();

  return (
    <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-xs ${statusDisplay.bg} ${statusDisplay.color}`}>
      <span>{statusDisplay.icon}</span>
      <span className="font-medium">{statusDisplay.text}</span>
    </div>
  );
};

export default ConnectionStatus;