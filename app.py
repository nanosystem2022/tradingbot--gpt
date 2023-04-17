import json
from flask import Flask, request
import ccxt

app = Flask(__name__)

with open('config.json') as config_file:
    config = json.load(config_file)

exchange = ccxt.binance({
    'apiKey': config['EXCHANGES']['BINANCE-FUTURES']['API_KEY'],
    'secret': config['EXCHANGES']['BINANCE-FUTURES']['API_SECRET'],
    'options': {
        'defaultType': 'future',
    },
    'urls': {
        'api': {
            'public': 'https://fapi.binance.com/fapi/v1',
            'private': 'https://fapi.binance.com/fapi/v1',
        },
    }
})

class Bot:

    def __init__(self):
        pass

    def close_position(self, symbol, side):
        position = exchange.fetch_positions(symbol)[0]['info']['positionAmt']
        params = {
            'reduceOnly': True
        }
        if side == 'long':
            exchange.create_order(symbol, 'Market', 'Sell', float(position), price=None, params=params)
        else:
            exchange.create_order(symbol, 'Market', 'Buy', -float(position), price=None, params=params)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    symbol = data['symbol']
    side = data['side']
    bot = Bot()

    if side == 'Buy' or side == 'Sell':
        exchange.create_order(symbol, 'Market', side)
    elif side == 'closelong':
        bot.close_position(symbol, 'long')
    elif side == 'closeshort':
        bot.close_position(symbol, 'short')

    return {'status': 'success'}

if __name__ == '__main__':
    app.run()
