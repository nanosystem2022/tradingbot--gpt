def handle_bybit_request(session: HTTP, data: dict):
    action = data['action']

    if action == 'create_order':
        create_order(session, data)
    else:
        print("Invalid action for Bybit")

def create_order(session: HTTP, data: dict):
    symbol = data['symbol']
    order_type = data['order_type']
    side = data['side']
    qty = data['qty']
    price = data['price']

    try:
        result = session.place_active_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            qty=qty,
            price=price,
            time_in_force="GoodTillCancel"
        )
        print("Order created:", result)
    except Exception as e:
        print("Error creating order:", e)
