import pandas as pd

inventory_data = [
    {"product_id": "PVR001", "product_name": "Salted Popcorn (Large)", "category": "Snacks", "quantity": 120, "retail_price": 450, "reorder_level": 30},
    {"product_id": "PVR002", "product_name": "Cheese Popcorn (Large)", "category": "Snacks", "quantity": 0, "retail_price": 550, "reorder_level": 25},
    {"product_id": "PVR003", "product_name": "Caramel Popcorn (Large)", "category": "Snacks", "quantity": 35, "retail_price": 550, "reorder_level": 25},
    {"product_id": "PVR004", "product_name": "Nachos with Cheese Dip", "category": "Snacks", "quantity": 0, "retail_price": 620, "reorder_level": 20},
    {"product_id": "PVR005", "product_name": "Veg Burger", "category": "Food", "quantity": 20, "retail_price": 280, "reorder_level": 15},
    {"product_id": "PVR006", "product_name": "Chicken Burger", "category": "Food", "quantity": 15, "retail_price": 350, "reorder_level": 10},
    {"product_id": "PVR007", "product_name": "French Fries (Large)", "category": "Snacks", "quantity": 50, "retail_price": 220, "reorder_level": 20},
    {"product_id": "PVR008", "product_name": "Cold Drink (Coke 500ml)", "category": "Beverages", "quantity": 80, "retail_price": 180, "reorder_level": 40},
    {"product_id": "PVR009", "product_name": "Cold Drink (Sprite 500ml)", "category": "Beverages", "quantity": 60, "retail_price": 180, "reorder_level": 40},
    {"product_id": "PVR010", "product_name": "Chocolate Brownie", "category": "Desserts", "quantity": 10, "retail_price": 250, "reorder_level": 5},
]

warehouse_data = [
    {"warehouse_id": "WH001", "warehouse_name": "Mumbai Central Warehouse", "product_id": "PVR002", "price": 165, "latitude": 19.0760, "longitude": 72.8777},
    {"warehouse_id": "WH002", "warehouse_name": "Andheri East Warehouse", "product_id": "PVR002", "price": 170, "latitude": 19.1136, "longitude": 72.8697},
    {"warehouse_id": "WH003", "warehouse_name": "Bandra Warehouse", "product_id": "PVR004", "price": 210, "latitude": 19.0596, "longitude": 72.8295},
    {"warehouse_id": "WH004", "warehouse_name": "Lower Parel Warehouse", "product_id": "PVR004", "price": 205, "latitude": 19.0033, "longitude": 72.8292},
    {"warehouse_id": "WH005", "warehouse_name": "Kurla Warehouse", "product_id": "PVR001", "price": 130, "latitude": 19.0726, "longitude": 72.8825},
    {"warehouse_id": "WH006", "warehouse_name": "Powai Warehouse", "product_id": "PVR001", "price": 135, "latitude": 19.1176, "longitude": 72.9060},
    {"warehouse_id": "WH007", "warehouse_name": "Vashi Warehouse", "product_id": "PVR003", "price": 150, "latitude": 19.0750, "longitude": 72.9980},
    {"warehouse_id": "WH008", "warehouse_name": "Chembur Warehouse", "product_id": "PVR003", "price": 148, "latitude": 19.0522, "longitude": 72.9005},
    {"warehouse_id": "WH009", "warehouse_name": "Goregaon Warehouse", "product_id": "PVR005", "price": 95, "latitude": 19.1663, "longitude": 72.8526},
    {"warehouse_id": "WH010", "warehouse_name": "Malad Warehouse", "product_id": "PVR005", "price": 92, "latitude": 19.1875, "longitude": 72.8484},
    {"warehouse_id": "WH011", "warehouse_name": "Kandivali Warehouse", "product_id": "PVR006", "price": 135, "latitude": 19.2094, "longitude": 72.8526},
    {"warehouse_id": "WH012", "warehouse_name": "Borivali Warehouse", "product_id": "PVR006", "price": 138, "latitude": 19.2307, "longitude": 72.8567},
    {"warehouse_id": "WH013", "warehouse_name": "Dadar Warehouse", "product_id": "PVR007", "price": 110, "latitude": 19.0176, "longitude": 72.8562},
    {"warehouse_id": "WH014", "warehouse_name": "Sion Warehouse", "product_id": "PVR007", "price": 108, "latitude": 19.0434, "longitude": 72.8630},
    {"warehouse_id": "WH015", "warehouse_name": "Thane Warehouse", "product_id": "PVR008", "price": 48, "latitude": 19.2183, "longitude": 72.9781},
    {"warehouse_id": "WH016", "warehouse_name": "Mulund Warehouse", "product_id": "PVR008", "price": 50, "latitude": 19.1726, "longitude": 72.9565},
    {"warehouse_id": "WH017", "warehouse_name": "Bhandup Warehouse", "product_id": "PVR009", "price": 47, "latitude": 19.1511, "longitude": 72.9372},
    {"warehouse_id": "WH018", "warehouse_name": "Ghatkopar Warehouse", "product_id": "PVR009", "price": 49, "latitude": 19.0856, "longitude": 72.9081},
    {"warehouse_id": "WH019", "warehouse_name": "Colaba Warehouse", "product_id": "PVR010", "price": 75, "latitude": 18.9067, "longitude": 72.8147},
    {"warehouse_id": "WH020", "warehouse_name": "Fort Warehouse", "product_id": "PVR010", "price": 78, "latitude": 18.9322, "longitude": 72.8347},
]

online_prices_data = [ 
    {"product_id": "PVR001", "platform": "Amazon", "online_price": 145, "rating": 4.5, "delivery_days": 1},
    {"product_id": "PVR001", "platform": "Flipkart", "online_price": 150, "rating": 4.2, "delivery_days": 2},
    {"product_id": "PVR002", "platform": "Amazon", "online_price": 185, "rating": 4.4, "delivery_days": 1},
    {"product_id": "PVR002", "platform": "Flipkart", "online_price": 190, "rating": 4.3, "delivery_days": 3},
    {"product_id": "PVR003", "platform": "Amazon", "online_price": 168, "rating": 4.6, "delivery_days": 2},
    {"product_id": "PVR003", "platform": "Flipkart", "online_price": 172, "rating": 4.5, "delivery_days": 1},
    {"product_id": "PVR004", "platform": "Amazon", "online_price": 235, "rating": 4.1, "delivery_days": 1},
    {"product_id": "PVR004", "platform": "Flipkart", "online_price": 240, "rating": 4.0, "delivery_days": 2},
    {"product_id": "PVR005", "platform": "Amazon", "online_price": 105, "rating": 4.2, "delivery_days": 1},
    {"product_id": "PVR005", "platform": "Flipkart", "online_price": 110, "rating": 4.1, "delivery_days": 2},
    {"product_id": "PVR006", "platform": "Amazon", "online_price": 155, "rating": 4.7, "delivery_days": 1},
    {"product_id": "PVR006", "platform": "Flipkart", "online_price": 158, "rating": 4.5, "delivery_days": 1},
    {"product_id": "PVR007", "platform": "Amazon", "online_price": 125, "rating": 4.0, "delivery_days": 2},
    {"product_id": "PVR007", "platform": "Flipkart", "online_price": 122, "rating": 3.9, "delivery_days": 3},
    {"product_id": "PVR008", "platform": "Amazon", "online_price": 55, "rating": 4.8, "delivery_days": 1},
    {"product_id": "PVR008", "platform": "Flipkart", "online_price": 58, "rating": 4.7, "delivery_days": 1},
    {"product_id": "PVR009", "platform": "Amazon", "online_price": 54, "rating": 4.8, "delivery_days": 1},
    {"product_id": "PVR009", "platform": "Flipkart", "online_price": 56, "rating": 4.7, "delivery_days": 1},
    {"product_id": "PVR010", "platform": "Amazon", "online_price": 88, "rating": 4.9, "delivery_days": 1},
    {"product_id": "PVR010", "platform": "Flipkart", "online_price": 85, "rating": 4.8, "delivery_days": 2},
]

online_prices_df = pd.DataFrame(online_prices_data)
inventory_df = pd.DataFrame(inventory_data)
warehouse_df = pd.DataFrame(warehouse_data)