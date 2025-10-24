/**
 * App State Context for managing global application state.
 * 
 * Provides:
 * - Session management
 * - Cart state
 * - Product search history
 * - Error handling
 */

import React, { createContext, useContext, useReducer, useEffect } from 'react';

export interface Product {
  id: string;
  name: string;
  description: string;
  price: number;
  category: string;
  image_url: string;
  in_stock: boolean;
  rating?: number;
  reviews_count?: number;
}

export interface CartItem {
  id: string;
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

export interface AppState {
  // Session
  sessionId: string | null;
  
  // Products
  searchResults: Product[];
  searchHistory: string[];
  
  // Cart
  cartItems: CartItem[];
  cartTotal: number;
  
  // UI State
  isLoading: boolean;
  error: string | null;
}

type AppAction =
  | { type: 'SET_SESSION_ID'; payload: string }
  | { type: 'SET_SEARCH_RESULTS'; payload: Product[] }
  | { type: 'ADD_SEARCH_QUERY'; payload: string }
  | { type: 'ADD_TO_CART'; payload: CartItem }
  | { type: 'UPDATE_CART_ITEM'; payload: { id: string; quantity: number } }
  | { type: 'REMOVE_FROM_CART'; payload: string }
  | { type: 'CLEAR_CART' }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null };

const initialState: AppState = {
  sessionId: null,
  searchResults: [],
  searchHistory: [],
  cartItems: [],
  cartTotal: 0,
  isLoading: false,
  error: null,
};

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_SESSION_ID':
      return {
        ...state,
        sessionId: action.payload,
      };
      
    case 'SET_SEARCH_RESULTS':
      return {
        ...state,
        searchResults: action.payload,
      };
      
    case 'ADD_SEARCH_QUERY':
      const newHistory = [action.payload, ...state.searchHistory.filter(q => q !== action.payload)];
      return {
        ...state,
        searchHistory: newHistory.slice(0, 10), // Keep last 10 searches
      };
      
    case 'ADD_TO_CART':
      const existingItemIndex = state.cartItems.findIndex(
        item => item.product_id === action.payload.product_id
      );
      
      let updatedItems;
      if (existingItemIndex >= 0) {
        // Update existing item
        updatedItems = state.cartItems.map((item, index) =>
          index === existingItemIndex
            ? {
                ...item,
                quantity: item.quantity + action.payload.quantity,
                total_price: (item.quantity + action.payload.quantity) * item.unit_price,
              }
            : item
        );
      } else {
        // Add new item
        updatedItems = [...state.cartItems, action.payload];
      }
      
      const newTotal = updatedItems.reduce((sum, item) => sum + item.total_price, 0);
      
      return {
        ...state,
        cartItems: updatedItems,
        cartTotal: newTotal,
      };
      
    case 'UPDATE_CART_ITEM':
      const updatedCartItems = state.cartItems.map(item =>
        item.id === action.payload.id
          ? {
              ...item,
              quantity: action.payload.quantity,
              total_price: action.payload.quantity * item.unit_price,
            }
          : item
      );
      
      const updatedTotal = updatedCartItems.reduce((sum, item) => sum + item.total_price, 0);
      
      return {
        ...state,
        cartItems: updatedCartItems,
        cartTotal: updatedTotal,
      };
      
    case 'REMOVE_FROM_CART':
      const filteredItems = state.cartItems.filter(item => item.id !== action.payload);
      const filteredTotal = filteredItems.reduce((sum, item) => sum + item.total_price, 0);
      
      return {
        ...state,
        cartItems: filteredItems,
        cartTotal: filteredTotal,
      };
      
    case 'CLEAR_CART':
      return {
        ...state,
        cartItems: [],
        cartTotal: 0,
      };
      
    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
      };
      
    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
      };
      
    default:
      return state;
  }
}

interface AppContextType extends AppState {
  // Actions
  createSession: () => Promise<void>;
  setSearchResults: (products: Product[]) => void;
  addSearchQuery: (query: string) => void;
  addToCart: (item: Omit<CartItem, 'id'>) => void;
  updateCartItem: (id: string, quantity: number) => void;
  removeFromCart: (id: string) => void;
  clearCart: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const useAppState = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppState must be used within an AppStateProvider');
  }
  return context;
};

export const AppStateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);
  
  // Prefer relative API URLs so Docker nginx or CRA proxy handles routing
  const API_URL = process.env.REACT_APP_API_URL || '';

  // Create a new session
  const createSession = async () => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      dispatch({ type: 'SET_ERROR', payload: null });
      
      const response = await fetch(`${API_URL}/api/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });
      
      if (!response.ok) {
        // Fail silently and let UI retry; do not spam console in startup race
        return;
      }
      
      const data = await response.json();
      dispatch({ type: 'SET_SESSION_ID', payload: data.session_id });
      
      // Store session ID in localStorage for persistence
      localStorage.setItem('ai_assistant_session_id', data.session_id);
      
    } catch (error) {
      // Avoid noisy console on startup; UI will retry/allow manual reconnect
      dispatch({ type: 'SET_ERROR', payload: 'Failed to create session' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  // Actions
  const setSearchResults = (products: Product[]) => {
    dispatch({ type: 'SET_SEARCH_RESULTS', payload: products });
  };

  const addSearchQuery = (query: string) => {
    dispatch({ type: 'ADD_SEARCH_QUERY', payload: query });
  };

  const addToCart = (item: Omit<CartItem, 'id'>) => {
    const cartItem: CartItem = {
      id: `cart_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      ...item,
    };
    dispatch({ type: 'ADD_TO_CART', payload: cartItem });
  };

  const updateCartItem = (id: string, quantity: number) => {
    if (quantity <= 0) {
      removeFromCart(id);
    } else {
      dispatch({ type: 'UPDATE_CART_ITEM', payload: { id, quantity } });
    }
  };

  const removeFromCart = (id: string) => {
    dispatch({ type: 'REMOVE_FROM_CART', payload: id });
  };

  const clearCart = () => {
    dispatch({ type: 'CLEAR_CART' });
  };

  const setLoading = (loading: boolean) => {
    dispatch({ type: 'SET_LOADING', payload: loading });
  };

  const setError = (error: string | null) => {
    dispatch({ type: 'SET_ERROR', payload: error });
  };

  // Load and validate session from localStorage on mount; if invalid, create a new one
  useEffect(() => {
    const savedSessionId = localStorage.getItem('ai_assistant_session_id');
    const validateOrCreate = async () => {
      if (!savedSessionId) {
        await createSession();
        return;
      }
      try {
        const res = await fetch(`${API_URL}/api/sessions/${savedSessionId}/context`);
        // If the server says this session doesn't exist (common after DB reset),
        // drop the cached id and create a fresh session.
        if (res.status === 404 || res.status === 410) {
          localStorage.removeItem('ai_assistant_session_id');
          await createSession();
          return;
        }
        if (!res.ok) {
          // Any other non-OK means we can't use the cached id; recreate.
          localStorage.removeItem('ai_assistant_session_id');
          await createSession();
          return;
        }
        // Valid session: use it.
        dispatch({ type: 'SET_SESSION_ID', payload: savedSessionId });
      } catch (e) {
        // Network hiccup: fall back to creating a new session
        localStorage.removeItem('ai_assistant_session_id');
        await createSession();
      }
    };
    // Fire and forget
    validateOrCreate();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const contextValue: AppContextType = {
    ...state,
    createSession,
    setSearchResults,
    addSearchQuery,
    addToCart,
    updateCartItem,
    removeFromCart,
    clearCart,
    setLoading,
    setError,
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};
