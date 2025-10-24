-- Initialize database with schema and sample data for the AI Product Discovery Assistant
-- Sample product data for testing
-- 1) Create table expected by the application
CREATE TABLE IF NOT EXISTS product (
  id                TEXT PRIMARY KEY,
  name              TEXT NOT NULL,
  description       TEXT,
  long_description  TEXT,
  price             NUMERIC(10,2) NOT NULL,
  category          TEXT,
  image_url         TEXT,
  additional_images JSONB,
  in_stock          BOOLEAN DEFAULT TRUE,
  stock_quantity    INTEGER DEFAULT 0,
  rating            NUMERIC(3,1),
  reviews_count     INTEGER DEFAULT 0,
  specifications    JSONB,
  features          JSONB,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO product (id, name, description, price, category, image_url, in_stock, stock_quantity, rating, reviews_count, specifications, features) VALUES
    ('prod_001', 'Wireless Bluetooth Headphones', 'Premium noise-cancelling wireless headphones with 30-hour battery life', 199.99, 'ELECTRONICS', 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=300&h=300&fit=crop', true, 25, 4.5, 1247, '{"brand": "TechSound", "model": "TS-1000", "warranty": "2 years", "connectivity": "Bluetooth 5.0", "battery_life": "30 hours", "weight": "250g"}', '["Active Noise Cancellation", "Quick Charge (10min = 5hours)", "Voice Assistant Compatible", "Foldable Design"]'),
    
    ('prod_002', 'Smartphone Protective Case', 'Ultra-slim transparent case with wireless charging support and drop protection', 29.99, 'ELECTRONICS', 'https://images.unsplash.com/photo-1556656793-08538906a9f8?w=300&h=300&fit=crop', true, 150, 4.2, 892, '{"material": "TPU + PC", "compatibility": "iPhone 14/15", "wireless_charging": true, "drop_protection": "10ft", "thickness": "1.2mm"}', '["Wireless Charging Compatible", "Military Grade Drop Protection", "Crystal Clear", "Precise Cutouts"]'),
    
    ('prod_003', '100% Organic Cotton T-Shirt', 'Comfortable premium cotton t-shirt available in multiple colors and sizes', 24.99, 'CLOTHING', 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=300&h=300&fit=crop', true, 200, 4.0, 3456, '{"material": "100% Organic Cotton", "care": "Machine Washable", "fit": "Regular", "weight": "180gsm", "origin": "USA"}', '["100% Organic Cotton", "Pre-shrunk", "Available in 12 Colors", "Sustainable Production"]'),
    
    ('prod_004', 'Smart Home Security Camera', 'AI-powered security camera with motion detection and night vision', 149.99, 'ELECTRONICS', 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=300&h=300&fit=crop', true, 45, 4.7, 567, '{"resolution": "4K Ultra HD", "field_of_view": "130 degrees", "night_vision": "Up to 30ft", "storage": "Cloud + Local", "ai_detection": true}', '["4K Ultra HD Recording", "AI Motion Detection", "Two-Way Audio", "Weather Resistant", "Mobile App Control"]'),
    
    ('prod_005', 'Ergonomic Office Chair', 'Premium ergonomic chair with lumbar support and adjustable height', 299.99, 'HOME', 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=300&h=300&fit=crop', true, 30, 4.6, 234, '{"material": "Mesh + Steel", "weight_capacity": "300lbs", "height_adjustment": "17-21 inches", "warranty": "5 years", "assembly": "Required"}', '["Lumbar Support", "Breathable Mesh", "360° Swivel", "Height Adjustable", "Armrest Support"]'),
    
    ('prod_006', 'Bestselling Mystery Novel', 'Gripping psychological thriller that kept readers turning pages all night', 14.99, 'BOOKS', 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=300&h=300&fit=crop', true, 75, 4.4, 12890, '{"pages": 342, "publisher": "Mystery House", "publication_year": 2023, "language": "English", "format": "Paperback"}', '["Bestseller List", "Award Winner", "Book Club Favorite", "Page Turner"]'),
    
    ('prod_007', 'Professional Tennis Racket', 'Tournament-grade tennis racket used by professional players worldwide', 189.99, 'SPORTS', 'https://images.unsplash.com/photo-1551698618-1dfe5d97d256?w=300&h=300&fit=crop', true, 20, 4.8, 445, '{"weight": "300g", "head_size": "98 sq in", "string_pattern": "16x19", "balance": "310mm", "grip_size": "4 1/4"}', '["Professional Grade", "Carbon Fiber Frame", "Shock Absorption", "Tournament Approved"]'),
    
    ('prod_008', 'Natural Face Moisturizer', 'Hydrating face cream with organic ingredients for all skin types', 39.99, 'BEAUTY', 'https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=300&h=300&fit=crop', true, 120, 4.3, 2156, '{"size": "50ml", "skin_type": "All Types", "spf": "SPF 15", "ingredients": "Organic", "cruelty_free": true}', '["Organic Ingredients", "Cruelty-Free", "SPF Protection", "Dermatologist Tested", "Fragrance-Free"]'),
    
    ('prod_009', 'Gaming Mechanical Keyboard', 'RGB backlit mechanical keyboard with programmable keys for gaming', 129.99, 'ELECTRONICS', 'https://images.unsplash.com/photo-1541140532154-b024d705b90a?w=300&h=300&fit=crop', true, 60, 4.5, 1789, '{"switch_type": "Cherry MX Blue", "backlight": "RGB", "connectivity": "USB-C", "key_rollover": "N-Key", "software": "Programmable"}', '["Mechanical Switches", "RGB Backlighting", "Programmable Keys", "Gaming Mode", "Anti-Ghosting"]'),
    
    ('prod_010', 'Stainless Steel Water Bottle', 'Insulated water bottle that keeps drinks cold for 24 hours or hot for 12 hours', 34.99, 'HOME', 'https://images.unsplash.com/photo-1523362628745-0c100150b504?w=300&h=300&fit=crop', true, 80, 4.1, 3421, '{"capacity": "750ml", "material": "Stainless Steel", "insulation": "Double Wall", "leak_proof": true, "bpa_free": true}', '["24h Cold / 12h Hot", "Leak-Proof Design", "BPA-Free", "Wide Mouth Opening", "Dishwasher Safe"]'),

    ('prod_011', 'Budget Office Keyboard', 'Quiet membrane keyboard ideal for office work', 19.99, 'ELECTRONICS', 'https://images.unsplash.com/photo-1555532538-dcdbd01d373d?w=300&h=300&fit=crop', true, 200, 4.0, 320, '{"interface": "USB", "layout": "Full-size"}', '["Quiet keys", "Spill resistant", "USB"]'),

    ('prod_012', '60% Mechanical Keyboard', 'Compact 60% layout with hot-swappable switches', 89.99, 'ELECTRONICS', 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300&h=300&fit=crop', true, 80, 4.6, 540, '{"layout": "60%", "hot_swappable": true}', '["Hot-swappable", "Compact", "PBT keycaps"]'),
    
    ('prod_013', 'Wireless Mouse', 'Ergonomic wireless mouse with long battery life', 29.99, 'ELECTRONICS', 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=300&h=300&fit=crop', true, 150, 4.3, 900, '{"connectivity": "2.4GHz", "dpi": 3200}', '["Ergonomic", "Adjustable DPI", "USB Receiver"]'),
    
    ('prod_014', '4K UHD Monitor 27"', 'Crisp 27-inch 4K IPS monitor with HDR support', 349.99, 'ELECTRONICS', 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300&h=300&fit=crop', true, 40, 4.7, 210, '{"resolution": "3840x2160", "panel": "IPS"}', '["4K UHD", "IPS", "HDR10"]'),
    
    ('prod_015', 'Ultrabook Laptop 14"', 'Lightweight laptop with 16GB RAM and 512GB SSD', 999.00, 'ELECTRONICS', 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300&h=300&fit=crop', true, 25, 4.4, 160, '{"ram": "16GB", "storage": "512GB SSD"}', '["Backlit keyboard", "Fingerprint sensor"]'),
    
    ('prod_016', 'Gaming Laptop 15.6"', 'RTX graphics, 144Hz display, 32GB RAM', 1499.00, 'ELECTRONICS', 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300&h=300&fit=crop', true, 15, 4.5, 380, '{"gpu": "RTX", "display": "144Hz"}', '["RGB keyboard", "Dual fan cooling"]'),
    
    ('prod_017', 'Bluetooth Speaker', 'Portable speaker with deep bass and 12h battery', 59.99, 'ELECTRONICS', 'https://images.unsplash.com/photo-1526256262350-7da7584cf5eb?w=300&h=300&fit=crop', true, 100, 4.4, 720, '{"battery": "12h", "water_resistant": true}', '["Bluetooth 5.0", "Deep bass"]'),
    
    ('prod_018', 'Mechanical Keyboard Under $50', 'Entry-level mechanical keyboard with blue switches', 49.99, 'ELECTRONICS', 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300&h=300&fit=crop', true, 120, 4.1, 440, '{"switches": "Blue", "layout": "Full-size"}', '["RGB", "Blue switches"]'),
    
    ('prod_019', 'Premium Mechanical Keyboard', 'Aluminum case, gasket mount, silent switches', 249.00, 'ELECTRONICS', 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300&h=300&fit=crop', true, 30, 4.8, 95, '{"case": "Aluminum", "mount": "Gasket"}', '["Silent switches", "Hot-swappable"]'),
    
    ('prod_020', 'Wireless Keyboard and Mouse Combo', 'Compact wireless keyboard with matching mouse', 39.99, 'ELECTRONICS', 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300&h=300&fit=crop', true, 180, 4.2, 610, '{"connection": "2.4GHz", "receiver": "USB"}', '["Wireless combo", "Long battery life"]')
ON CONFLICT (id) DO NOTHING;
