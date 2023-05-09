import json
from flask import Flask, render_template, request, jsonify
import time
import ccxt
from custom_http import HTTP

app = Flask(__name__)

# load config.json
with open('config.json') as config_file:
    config = json.load(config_file)

current_position = 'closed'

def is_exchange_enabled(exchange_name):
    if exchange_name in config['EXCHANGES']:
        if config['EXCHANGES'][exchange_name]['ENABLED']:
            return True
    return False

def create_order_binance(data, exchange):
    try:
        symbol = data['symbol']
        order_type = data['type']
        side = data['side']
        quantity = data['quantity']

        if side == "closelong" and current_position == "long":
            side = "sell"
        elif side == "closeshort" and current_position == "short":
            side = "buy"
        else:
            return {"status": "error", "message": "Invalid side or position state."}, 400

        if order_type == "market":
            order = exchange.create_market_order(symbol, side, quantity)
        elif order_type == "limit":
            price = data['price']
            order = exchange.create_limit_order(symbol, side, quantity, price)
        else:
            return {"status": "error", "message": "Invalid order type"}, 400

        return {"status": "success", "data": order}, 200
    except Exception as e:
        return {"status": "error", "message": f"Error creating order: {str(e)}"}, 500


def create_order_bybit(data, session):
    symbol = data['symbol']
    side = data['side']
    price = data.get('price', 0)
    quantity = data.get('quantity')

    if quantity is None:
        error_message = "The 'quantity' field is missing in the input data."
        return {
            "status": "error",
            "message": error_message
        }, 400

    try:
        if side == "closelong" and current_position == "long":
            side = "sell"
        elif side == "closeshort" and current_position == "short":
            side = "buy"
        else:
            return {"status": "error", "message": "Invalid side or position state."}, 400

        order = session.post('/v2/private/order/create', json={
            'symbol': symbol,
            'side': side,
            'order_type': data['type'],
            'qty': float(quantity),
            'price': price,
            'time_in_force': 'GTC'
        })
        return {
            "status": "success",
            "data": order.json()
        }, 200
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }, 500

# Other code remains the same

@app.route('/webhook', methods=['POST'])
def webhook():
    global current_position
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

    close_order = data['side'] == 'closelong' or data['side'] == 'closeshort'
    if current_position == 'closed' or close_order:
        if data['exchange'] == 'binance-futures':
            if use_binance_futures:
                response, status_code = create_order_binance(data, exchange)
                if data['side'] == 'long' or data['side'] == 'short':
                    current_position = data['side']
                return jsonify(response), status_code
            else:
                error_message = "Binance Futures is not enabled in the config file."
                return {
                    "status": "error",
                    "message": error_message
                }, 400

        elif data['exchange'] == 'bybit':
            if use_bybit:
                response, status_code = create_order_bybit(data, session)
                if data['side'] == 'long' or data['side'] == 'short':
                    current_position = data['side']
                return jsonify(response), status_code
            else:
                error_message = "Bybit is not enabled in the config file."
                return {
                    "status": "error",
                    "message": error_message
                }, 400

        else:
            error_message = "Unsupported exchange."
            return {
                "status": "error",
                "message": error_message
            }, 400

        if close_order:
            current_position = 'closed'

    else:
        error_message = "Cannot accept new orders until current position is closed."
        return {
            "status": "error",
            "message": error_message
        }, 400

if __name__ == '__main__':
    app.run()
