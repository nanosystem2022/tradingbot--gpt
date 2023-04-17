import ccxt

def handle_binance_request(exchange: ccxt.binance, data: dict):
    action = data['action']

    if action == 'create_order':
        create_order(exchange, data)
    else:
        print("Invalid action for Binance Futures")

def create_order(exchange: ccxt.binance, data: dict):
    symbol = data['symbol']
    order_type = data['order_type']
    side = data['side']
    amount = data['amount']

    try:
        result = exchange.create_order(symbol, order_type, side, amount)
        print("Order created:", result)
    except Exception as e:
        print("Error creating order:", e)
