/**
 * Function Call Renderer - Dynamically renders components based on AI function calls
 * 
 * TODO: This is a key component that maps AI function calls to React components.
 * Implement the component mapping and rendering logic.
 */

import React from 'react';
interface FunctionCall {
  name: string;
  parameters: Record<string, any>;
  result?: any;
}

interface FunctionCallRendererProps {
  functionCall: FunctionCall;
  onInteraction?: (action: string, data: any) => void;
}

// Search results list
const SearchResults: React.FC<any> = ({ products = [], onProductSelect }) => {
  return (
    <div className="border rounded-lg p-4 bg-blue-50">
      <h3 className="font-medium text-blue-900 mb-3">Search Results</h3>
      {products.length === 0 ? (
        <p className="text-sm text-blue-700">No products found.</p>
      ) : (
        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {products.map((p: any) => (
            <li key={p.id} className="bg-white rounded-lg p-3 product-card border">
              <div className="flex">
                <img
                  src={p.image_url}
                  alt={p.name}
                  className="w-16 h-16 rounded object-cover mr-3"
                  onError={(e) => {
                    const img = e.currentTarget as HTMLImageElement;
                    img.onerror = null; // prevent loop
                  }}
                />
                <div className="flex-1">
                  <div className="font-medium text-gray-900">{p.name}</div>
                  <div className="text-sm text-gray-600 line-clamp-2">{p.description}</div>
                  <div className="text-sm text-gray-900 font-semibold mt-1">${p.price?.toFixed?.(2) ?? p.price}</div>
                  <div className="mt-2">
                    <button
                      className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
                      onClick={() => onProductSelect?.(p.id)}
                    >
                      View details
                    </button>
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

// Product details card
const ProductCard: React.FC<any> = ({ product, recommendations = [], onAddToCart }) => {
  if (!product) return null;
  return (
    <div className="border rounded-lg p-4 bg-green-50">
      <div className="flex mb-3">
        <img
          src={product.image_url}
          alt={product.name}
          className="w-24 h-24 rounded object-cover mr-4"
          onError={(e) => {
            const img = e.currentTarget as HTMLImageElement;
            img.onerror = null; // prevent loop
          }}
        />
        <div className="flex-1">
          <h3 className="font-medium text-green-900 text-lg">{product.name}</h3>
          <div className="text-sm text-gray-700">{product.description}</div>
          <div className="font-semibold mt-1 text-gray-900">${product.price?.toFixed?.(2) ?? product.price}</div>
          <button
            className="mt-2 text-sm px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700"
            onClick={() => onAddToCart?.(product.id, 1)}
          >
            Add to cart
          </button>
        </div>
      </div>
      {recommendations.length > 0 && (
        <div>
          <div className="text-sm font-medium text-green-900 mb-2">You may also like</div>
          <div className="grid grid-cols-2 gap-2">
            {recommendations.map((r: any) => (
              <div key={r.id} className="bg-white rounded p-2 border">
                <div className="text-xs font-medium">{r.name}</div>
                <div className="text-xs">${r.price?.toFixed?.(2) ?? r.price}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Cart notification
const CartNotification: React.FC<any> = ({ cartItem }) => (
  <div className="border rounded-lg p-4 bg-purple-50">
    <h3 className="font-medium text-purple-900 mb-2">Added to Cart</h3>
    <p className="text-sm text-purple-700">
      {cartItem?.quantity} × {cartItem?.product_name} added. Total ${cartItem?.total_price?.toFixed?.(2) ?? cartItem?.total_price}
    </p>
  </div>
);

// Cart view
const CartView: React.FC<any> = ({ items = [], cart_summary, onInteraction }) => (
  <div className="border rounded-lg p-4 bg-purple-50">
    <h3 className="font-medium text-purple-900 mb-2">Your Cart</h3>
    {items.length === 0 ? (
      <p className="text-sm text-purple-700">Your cart is empty.</p>
    ) : (
      <div className="space-y-2">
        {items.map((it: any) => (
          <div key={it.id} className="bg-white rounded p-2 border flex justify-between items-center">
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{it.product_name}</div>
              <div className="text-xs text-gray-600">${it.unit_price?.toFixed?.(2) ?? it.unit_price} each</div>
            </div>
            <div className="flex items-center space-x-2">
              <button
                className="text-xs px-2 py-1 bg-gray-200 rounded hover:bg-gray-300"
                onClick={() => onInteraction?.('update_cart', { product_id: it.product_id, delta: -1 })}
                aria-label={`Decrease quantity of ${it.product_name}`}
              >
                −
              </button>
              <div className="text-sm w-6 text-center">{it.quantity}</div>
              <button
                className="text-xs px-2 py-1 bg-gray-200 rounded hover:bg-gray-300"
                onClick={() => onInteraction?.('update_cart', { product_id: it.product_id, delta: +1 })}
                aria-label={`Increase quantity of ${it.product_name}`}
              >
                +
              </button>
            </div>
            <div className="text-sm font-semibold w-20 text-right">${it.total_price?.toFixed?.(2) ?? it.total_price}</div>
            <button
              className="ml-3 text-xs px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700"
              onClick={() => onInteraction?.('remove_from_cart', { item_id: it.id, product_id: it.product_id })}
            >
              Remove
            </button>
          </div>
        ))}
        <div className="pt-2 mt-2 border-t text-sm">
          <div className="flex justify-between"><span>Items</span><span>{cart_summary?.total_items ?? 0}</span></div>
          <div className="flex justify-between"><span>Subtotal</span><span>${cart_summary?.subtotal?.toFixed?.(2) ?? cart_summary?.subtotal}</span></div>
          <div className="flex justify-between"><span>Est. Tax</span><span>${cart_summary?.estimated_tax?.toFixed?.(2) ?? cart_summary?.estimated_tax}</span></div>
          <div className="flex justify-between font-semibold"><span>Total</span><span>${cart_summary?.estimated_total?.toFixed?.(2) ?? cart_summary?.estimated_total}</span></div>
        </div>
      </div>
    )}
  </div>
);

// Recommendations grid
const RecommendationGrid: React.FC<any> = ({ recommendations = [], onProductSelect }) => (
  <div className="border rounded-lg p-4 bg-orange-50">
    <h3 className="font-medium text-orange-900 mb-2">Recommendations</h3>
    {recommendations.length === 0 ? (
      <p className="text-sm text-orange-700">No recommendations yet.</p>
    ) : (
      <div className="grid grid-cols-2 gap-3">
        {recommendations.map((r: any) => (
          <div key={r.id} className="bg-white rounded p-2 border product-card">
            <div className="text-sm font-medium">{r.name}</div>
            <div className="text-xs">${r.price?.toFixed?.(2) ?? r.price}</div>
            <button
              className="mt-2 text-xs px-2 py-1 bg-orange-600 text-white rounded hover:bg-orange-700"
              onClick={() => onProductSelect?.(r.id)}
            >
              View
            </button>
          </div>
        ))}
      </div>
    )}
  </div>
);

// Function call mapping - Maps AI function names to React components
const FunctionComponents: Record<string, React.ComponentType<any>> = {
  search_products: SearchResults,
  show_product_details: ProductCard,
  add_to_cart: CartNotification,
  get_recommendations: RecommendationGrid,
  get_cart: CartView,
  remove_from_cart: CartView
};

// Generic error banner for tool/validation errors
const ErrorBanner: React.FC<{ title?: string; message: string; suggestions?: any[] }> = ({ title = 'Validation Error', message, suggestions }) => (
  <div className="border rounded-lg p-4 bg-red-50">
    <h3 className="font-medium text-red-900 mb-2">{title}</h3>
    <p className="text-sm text-red-700">{message}</p>
    {Array.isArray(suggestions) && suggestions.length > 0 && (
      <div className="mt-2 text-xs text-red-700">
        <div className="font-medium mb-1">Did you mean:</div>
        <ul className="list-disc ml-5">
          {suggestions.slice(0, 5).map((s: any, idx: number) => (
            <li key={idx}>{typeof s === 'string' ? s : (s?.product_id || JSON.stringify(s))}</li>
          ))}
        </ul>
      </div>
    )}
  </div>
);

const FunctionCallRenderer: React.FC<FunctionCallRendererProps> = ({
  functionCall,
  onInteraction
}) => {
  const { name, parameters, result } = functionCall;
  
  // Get the component for this function call
  const normalizedName = (name || '').trim();
  const Component = FunctionComponents[normalizedName] ||
    // Fallback: any unknown function that returns cart shape still renders cart view
    (normalizedName.includes('cart') ? CartView : undefined);
  
  if (!Component) {
    return (
      <div className="border rounded-lg p-4 bg-gray-50">
        <h3 className="font-medium text-gray-900 mb-2">Unknown Function Call</h3>
        <p className="text-sm text-gray-600">
          Function "{name}" not implemented
        </p>
        <div className="mt-2 text-xs text-gray-500">
          Parameters: {JSON.stringify(parameters, null, 2)}
        </div>
      </div>
    );
  }

  // Handle different function call types
  const handleInteraction = (action: string, data: any) => {
    console.log('Function interaction:', { function: name, action, data });
    onInteraction?.(action, { function: name, ...data });
  };

  // Render the appropriate component with function call data
  try {
    // Normalize function result props so components get the shape they expect
    const raw = (result?.data || result || {}) as Record<string, any>;
    const mappedProps: Record<string, any> = { ...parameters, ...raw };

    if (normalizedName === 'add_to_cart') {
      // CartNotification expects `cartItem`, backend returns `cart_item`
      mappedProps.cartItem = raw.cartItem ?? raw.cart_item;
      mappedProps.cart_summary = raw.cart_summary ?? raw.cartSummary;
    }

    if (normalizedName === 'get_cart' || normalizedName === 'remove_from_cart') {
      // CartView already expects { items, cart_summary }
    }

    // Show validation/tool errors to the user instead of a blank card
    const validation = raw.validation as any;
    const hasValidationError = normalizedName === 'show_product_details' && (
      !raw.product || (validation && validation.valid === false)
    );
    const genericError = typeof raw.error === 'string' ? raw.error : null;

    if (genericError) {
      return (
        <div className="my-4">
          <ErrorBanner message={genericError} />
        </div>
      );
    }

    if (hasValidationError) {
      const message = validation?.error || 'Product not found or not in recent searches.';
      const suggestions = validation?.suggestions;
      return (
        <div className="my-4">
          <ErrorBanner title="Invalid Product ID" message={message} suggestions={suggestions} />
        </div>
      );
    }
    return (
      <div className="my-4">
        <Component
          {...mappedProps}
          onInteraction={handleInteraction}
          onProductSelect={(id: string) => handleInteraction('select_product', { product_id: id })}
          onAddToCart={(id: string, quantity: number) => handleInteraction('add_to_cart', { product_id: id, quantity })}
        />
      </div>
    );
  } catch (error) {
    console.error('Error rendering function call component:', error);
    
    return (
      <div className="border rounded-lg p-4 bg-red-50">
        <h3 className="font-medium text-red-900 mb-2">Render Error</h3>
        <p className="text-sm text-red-700">
          Failed to render component for function "{name}"
        </p>
        <div className="mt-2 text-xs text-red-600">
          {error instanceof Error ? error.message : 'Unknown error'}
        </div>
      </div>
    );
  }
};

export default FunctionCallRenderer;
