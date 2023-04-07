import ccxt
from flask import Flask, request

app = Flask(__name__)

# Initialize the exchanges

exchanges = {}
config = {
    "BYBIT": {
        "API_KEY": "",
        "API_SECRET": "",
        "ENABLED": False,
        "TESTNET": False
    },
    "BINANCE": {
        "API_KEY": "",
        "API_SECRET": "",
        "ENABLED": False,
        "TESTNET": False
    },
    "BINANCE_TESTNET": {
        "API_KEY": "18cdb3cc1757b7e14d678009713ab9506257dd28366bc9852df83ed46c89f135",
        "API_SECRET": "d45b531786836d30a2fd35ea5f5ec8a564cfb6c1baa768ebb4be01cab004c745",
        "ENABLED": True,
        "TESTNET": True
    }
}

for exchange_id, exchange_params in config.items():
    if exchange_params['ENABLED']:
        exchange = getattr(ccxt, exchange_id)({
            'apiKey': exchange_params['API_KEY'],
            'secret': exchange_params['API_SECRET'],
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
                'defaultTimeInForce': 'GTC',
            }
        })
        exchanges[exchange_id] = exchange

# Dictionary to store open positions
open_positions = {}

# Dictionary to store order ids
order_ids = {}

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if 'type' in data and data['type'] == 'order':
        symbol = data['symbol']
        if symbol not in open_positions:
            # Do not open a position if there is no open position for this symbol
            return 'No open position for symbol {}'.format(symbol)
        if data['side'] == 'sell' and open_positions[symbol]['side'] == 'long':
            # Close long position
            exchange_id = open_positions[symbol]['exchange']
            exchange = exchanges[exchange_id]
            order = exchange.create_order(
                symbol=symbol,
                type='market',
                side='sell',
                amount=open_positions[symbol]['amount'],
                params={
                    'positionSide': 'LONG',
                    'reduceOnly': True,
                }
            )
            order_ids[symbol] = order['id']
            return 'Closed long position for symbol {}'.format(symbol)
        elif data['side'] == 'buy' and open_positions[symbol]['side'] == 'short':
            # Close short position
            exchange_id = open_positions[symbol]['exchange']
            exchange = exchanges[exchange_id]
            order = exchange.create_order(
                symbol=symbol,
                type='market',
                side='buy',
                amount=open_positions[symbol]['amount'],
                params={
                    'positionSide': 'SHORT',
                    'reduceOnly': True,
                }
            )
            order_ids[symbol] = order['id']
            return 'Closed short position for symbol {}'.format(symbol)
    elif 'type' in data and data['type'] == 'close':
        symbol = data['symbol']
        if symbol not in open_positions:
            # Do not attempt to close a position if there is no open position for this symbol
            return 'No open position for symbol {}'.format(symbol)
        order_id = order_ids.get(symbol)
        if order_id is None:
            # No order id for this symbol, cannot close position
            return 'No order id for symbol {}, cannot close position'.format(symbol)
        # Check if the order is already closed
        if order_id in closed_orders:
            return 'Order for symbol {} is already closed'.format(symbol)
        # Check if the order is pending
        if order_id in pending_orders:
            return 'Order for symbol {} is still pending'.format(symbol)
        # Close the order
        order_result = exchange.close_order(order_id)
        if order_result['status'] == 'closed':
            # Remove the position from the open_positions dictionary
            del open_positions[symbol]
            # Add the position to the closed_positions dictionary
            closed_positions[symbol] = order_result['result']
            # Add the order id to the closed_orders set
            closed_orders.add(order_id)
            # Remove the order id from the order_ids dictionary
            del order_ids[symbol]
            return 'Position for symbol {} closed successfully'.format(symbol)
        else:
            return 'Failed to close position for symbol {}. Reason: {}'.format(symbol, order_result['reason'])
if __name__ == '__main__':
    # Set up the WebSocket connection
    ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/!ticker@arr", on_message=on_message)

    # Set up the API connection
    client = Client(api_key, api_secret)

    # Start the WebSocket connection in a new thread
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()

    # Run the Flask app on the main thread
    app.run(host='0.0.0.0', port=5000)

