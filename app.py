import os
import ccxt
import json
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

with open('config.json') as config_file:
    config = json.load(config_file)

# Adding a queue to store pending orders when a position is open
pending_orders = []

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print(f"Received data: {data}")

    if not validate_data(data):
        return "Invalid data", 400

    try:
        execute_trade(data)
    except Exception as e:
        print(f"Error executing trade: {e}")
        return "Error executing trade", 500

    return "Success", 200

def validate_data(data):
    if 'exchange' not in data or data['exchange'] not in config['EXCHANGES']:
        return False
    return True

def execute_trade(data):
    exchange = getattr(ccxt, data['exchange'].lower())({
        'apiKey': config['EXCHANGES'][data['exchange']]['API_KEY'],
        'secret': config['EXCHANGES'][data['exchange']]['API_SECRET'],
    })

    if config['EXCHANGES'][data['exchange']].get('TESTNET', False):
        exchange.set_sandbox_mode(True)

    symbol = data['symbol']
    market = data['market']
    order_type = data['type']

    # Fetch current position
    position = exchange.fetch_position(symbol)
    position_open = position['side'] != 'none'

    if order_type == 'buy' or order_type == 'sell':
        if not position_open:
            if order_type == 'buy':
                exchange.create_market_buy_order(symbol, market)
            else:
                exchange.create_market_sell_order(symbol, market)

            # If there are any pending orders, remove them
            pending_orders.clear()
        else:
            print("Position is already open. Adding the order to the pending orders list.")
            pending_orders.append(data)
    elif order_type == 'close-long':
        if position_open and position['side'] == 'long':
            exchange.create_market_sell_order(symbol, position['size'])

            # Execute the first pending order after closing the position
            if pending_orders:
                first_pending_order = pending_orders.pop(0)
                execute_trade(first_pending_order)
    elif order_type == 'close-short':
        if position_open and position['side'] == 'short':
            exchange.create_market_buy_order(symbol, position['size'])

            # Execute the first pending order after closing the position
            if pending_orders:
                first_pending_order = pending_orders.pop(0)
                execute_trade(first_pending_order)
    else:
        print("Invalid order type")

if __name__ == '__main__':
    app.run()
