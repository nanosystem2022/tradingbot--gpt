import json
import os
from flask import Flask, request, jsonify
import ccxt
from custom_http import HTTP

app = Flask(__name__)

# Load config.json
with open(os.getenv('CONFIG_FILE', 'config.json')) as config_file:
    config = json.load(config_file)

current_position = 'closed'
current_side = None
exchanges = {}

def is_exchange_enabled(exchange_name):
    """Check if the exchange is enabled in the config."""
    return exchange_name in config['EXCHANGES'] and config['EXCHANGES'][exchange_name]['ENABLED']

def initialize_exchanges():
    """Initialize enabled exchanges."""
    if is_exchange_enabled('BYBIT'):
        print("Bybit is enabled!")
        exchanges['bybit'] = HTTP(
            endpoint='https://api.bybit.com',
            api_key=config['EXCHANGES']['BYBIT']['API_KEY'],
            api_secret=config['EXCHANGES']['BYBIT']['API_SECRET']
        )

    if is_exchange_enabled('BINANCE-FUTURES'):
        print("Binance is enabled!")
        exchanges['binance-futures'] = ccxt.binance({
            'apiKey': config['EXCHANGES']['BINANCE-FUTURES']['API_KEY'],
            'secret': config['EXCHANGES']['BINANCE-FUTURES']['API_SECRET'],
            'options': {
                'defaultType': 'future',
            },
            'urls': {
                'api': {
                    'public': 'https://testnet.binancefuture.com/fapi/v1',
                    'private': 'https://testnet.binancefuture.com/fapi/v1',
                },
            }
        })

        if config['EXCHANGES']['BINANCE-FUTURES']['TESTNET']:
            exchanges['binance-futures'].set_sandbox_mode(True)

    if is_exchange_enabled('BINANCE-SPOT'):
        print("Binance Spot is enabled!")
        exchanges['binance-spot'] = ccxt.binance({
            'apiKey': config['EXCHANGES']['BINANCE-SPOT']['API_KEY'],
            'secret': config['EXCHANGES']['BINANCE-SPOT']['API_SECRET'],
            'options': {
                'defaultType': 'spot',
            }
        })

initialize_exchanges()

def create_order(data, exchange):
    """Create a new order on the exchange."""
    symbol = data['symbol']
    order_type = data['type']
    side = data['side']
    quantity = data['quantity']

    if side == "closelong":
        side = "sell"
    elif side == "closeshort":
        side = "buy"

    if order_type == "market":
        order = exchange.create_market_order(symbol, side, quantity)
    elif order_type == "limit":
        price = data['price']
        order = exchange.create_limit_order(symbol, side, quantity, price)
    else:
        raise ValueError("Invalid order type")

    return order

def close_order(data, exchange):
    """Close an existing order on the exchange."""
    symbol = data['symbol']
    side = data['side']
    price = data.get('price', 0)
    quantity = data.get('quantity')

    if side not in ['closelong', 'closeshort']:
        raise ValueError("Invalid side value for closing order. Use 'closelong' or 'closeshort'.")

    if quantity is None:
        raise ValueError("The 'quantity' field is missing in the input data.")

    order = exchange.create_order(
        symbol=symbol,
        type=data['type'],
        side='sell' if side == 'closelong' else 'buy',
        amount=float(quantity),
        price=price
    )
    return order

def can_open_order(current_position):
    """Check if a new order can be opened."""
    return current_position == 'closed'

def can_close_order(current_position, current_side, side):
    """Check if the current order can be closed."""
    return current_position == 'open' and ((current_side == 'buy' and side == 'closelong') or (current_side == 'sell' and side == 'closeshort'))

def handle_error(e):
    """Handle exceptions and return a response with an error message."""
    return {"status": "error", "message": str(e)}, 400 if isinstance(e, ValueError) else 500

@app.route('/webhook1', methods=['POST'])
def webhook():
    """Handle incoming webhook requests."""
    global current_position, current_side
    print("Hook Received!")
    data = request.get_json(force=True)  # This will ensure the data is JSON

    if not data:
        return {"status": "error", "message": "No data provided"}, 400

    if 'key' not in data or int(data['key']) != config['KEY']:
        error_message = "Invalid Key, Please Try Again!"
        print(error_message)
        return {
            "status": "error",
            "message": error_message
        }, 400

    try:
        exchange = exchanges.get(data['exchange'])
        if not exchange:
            raise ValueError(f"{data['exchange']} is not enabled in the config file.")

        if data['side'] in ['buy', 'sell']:
            if can_open_order(current_position):
                response = create_order(data, exchange)
                current_position = 'open'
                current_side = data['side']
            else:
                raise ValueError("Cannot open a new order until the current one is closed.")
        elif data['side'] in ['closelong', 'closeshort']:
            if can_close_order(current_position, current_side, data['side']):
                response = close_order(data, exchange)
                current_position = 'closed'
            else:
                raise ValueError("Cannot close the order. Either there is no open order or the side of the closing order does not match the side of the open order.")
        else:
            raise ValueError("Invalid side value. Use 'buy', 'sell', 'closelong' or 'closeshort'.")

        return {"status": "success", "data": response}, 200

    except Exception as e:
        return handle_error(e)

if __name__ == '__main__':
    app.run(host=os.getenv('FLASK_HOST', '0.0.0.0'), port=int(os.getenv('FLASK_PORT', 5000)))
