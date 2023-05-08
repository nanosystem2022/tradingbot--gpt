
    if symbol in user_trade_status:
        if side == 'closelong' and user_trade_status

    symbol = data['symbol']
    side = data['side']

    if symbol in user_trade_status:
        if side == 'closelong' and user_trade_status[symbol] != 'buy':
            return {"status": "error", "message": "Cannot close long because there is no open long position."}, 400
        if side == 'closeshort' and user_trade_status[symbol] != 'sell':
            return {"status": "error", "message": "Cannot close short because there is no open short position."}, 400

    if data['exchange'] == 'binance-futures':
        if use_binance_futures:
            response, status_code = create_order_binance(data, exchange)
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

if __name__ == '__main__':
    app.run()
