import json
import os
from flask import Flask, render_template, request, jsonify
import time
import ccxt
from custom_http import HTTP

app = Flask(__name__)

# Load config.json
with open('config.json') as config_file:
    config = json.load(config_file)

current_position = 'closed'
current_side = None

def is_exchange_enabled(exchange_name):
    """Check if the exchange is enabled in the config."""
    return exchange_name in config['EXCHANGES'] and config['EXCHANGES'][exchange_name]['ENABLED']

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

def handle_error(e):
    """Handle exceptions and return a response with an error message."""
    return {"status": "error", "message": str(e)}, 400 if isinstance(e, ValueError) else 500

def can_open_order(current_position):
    """Check if a new order can be opened."""
    return current_position == 'closed'

def can_close_order(current_position, current_side, side):
    """Check if the current order can be closed."""
    return current_position == 'open' and ((current_side == 'buy' and side == 'closelong') or (current_side == 'sell' and side == 'closeshort'))

use_bybit = is_exchange_enabled('BYBIT')
use_binance_futures = is_exchange_enabled('BINANCE-FUTURES')
use_binance_spot = is_exchange_enabled('BINANCE-SPOT')

if use_bybit:
    print("Bybit is enabled!")
    session = HTTP(
        endpoint='https://api.bybit.com',
        api_key=config['EXCHANGES']['BYBIT']['API_KEY'],
        api_secret=config['EXCHANGES']['BYBIT']['API_SECRET']
    )

if use_binance_futures:
    print("Binance is enabled!")
    exchange = ccxt.binance({
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
        exchange.set_sandbox_mode(True)

if use_binance_spot:
    print("Binance Spot is enabled!")
    exchange_spot = ccxt.binance({
        'apiKey': config['EXCHANGES']['BINANCE-SPOT']['API_KEY'],
        'secret': config['EXCHANGES']['BINANCE-SPOT']['API_SECRET'],
        'options': {
            'defaultType': 'spot',
        }
    })

@app.route('/webhook1', methods=['POST'])
def webhook():
    """Handle incoming webhook requests."""
    global current_position, current_side
    print("Hook Received!")
    data = json.loads(request.data)
    print(data)

    if int(data['key']) != config['KEY']:
        error_message = "Invalid Key, Please Try Again!"
        print(error_message)
        return {
            "status": "error",
            "message": error_message
        }, 400

    try:
        if data['exchange'] == 'binance-futures':
            if use_binance_futures:
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
            else:
                raise ValueError("Binance Futures is not enabled in the config file.")

        elif data['exchange'] == 'binance-spot':
            if use_binance_spot:
                if data['side'] in ['buy', 'sell']:
                    if can_open_order(current_position):
                        response = create_order(data, exchange_spot)
                        current_position = 'open'
                        current_side = data['side']
                    else:
                        raise ValueError("Cannot open a new order until the current one is closed.")
                else:
                    raise ValueError("Invalid side value. Use 'buy' or 'sell'.")
                return {"status": "success", "data": response}, 200
            else:
                raise ValueError("Binance Spot is not enabled in the config file.")

        elif data['exchange'] == 'bybit':
            if use_bybit:
                if data['side'] in ['buy', 'sell']:
                    if can_open_order(current_position):
                        response = create_order_bybit(data, session)
                        current_position = 'open'
                        current_side = data['side']
                    else:
                        raise ValueError("Cannot open a new order until the current one is closed.")
                elif data['side'] in ['closelong', 'closeshort']:
                    if can_close_order(current_position, current_side, data['side']):
                        response = close_order_bybit(data, session)
                        current_position = 'closed'
                    else:
                        raise ValueError("Cannot close the order. Either there is no open order or the side of the closing order does not match the side of the open order.")
                else:
                    raise ValueError("Invalid side value. Use 'buy', 'sell', 'closelong' or 'closeshort'.")
                return {"status": "success", "data": response}, 200
            else:
                raise ValueError("Bybit is not enabled in the config file.")

        else:
            raise ValueError("Unsupported exchange.")

    except Exception as e:
        return handle_error(e)

if __name__ == '__main__':
    app.run()
