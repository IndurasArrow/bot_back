from data import inventory_df, warehouse_df, online_prices_df


def get_out_of_stock_price_report():
    """
    Returns a flat, LLM-friendly text report
    for all out-of-stock products.
    """

    out_of_stock_df = inventory_df[inventory_df["quantity"] == 0]

    if out_of_stock_df.empty:
        return "All products are currently in stock."

    blocks = []

    for _, product in out_of_stock_df.iterrows():
        product_id = product["product_id"]

        block = []
        block.append(f"Product ID: {product_id}")
        block.append(f"Product Name: {product['product_name']}")
        block.append(f"Category: {product['category']}")
        block.append(f"Retail Price: ₹{product['retail_price']}")
        block.append("Stock Status: OUT OF STOCK")

        # Warehouse prices
        warehouses = warehouse_df[warehouse_df["product_id"] == product_id]
        if not warehouses.empty:
            block.append("Warehouse Options:")
            for _, w in warehouses.iterrows():
                block.append(
                    f"- {w['warehouse_name']}: ₹{w['price']} "
                    f"(Lat: {w['latitude']}, Lng: {w['longitude']})"
                )
        else:
            block.append("Warehouse Options: None")

        # Online prices
        online = online_prices_df[online_prices_df["product_id"] == product_id]
        if not online.empty:
            block.append("Online Vendor Options:")
            for _, o in online.iterrows():
                block.append(
                    f"- {o['platform']}: ₹{o['online_price']} | "
                    f"Rating: {o['rating']} | "
                    f"Delivery: {o['delivery_days']} days"
                )
        else:
            block.append("Online Vendor Options: None")

        blocks.append("\n".join(block))

    return "\n\n---\n\n".join(blocks)

# print(get_out_of_stock_price_report())