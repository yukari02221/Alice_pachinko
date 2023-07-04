import asyncio
import ccxt
from collections import deque
from pprint import pprint

api_key = ''
api_secret = ''

#privatekey
exchange = ccxt.bitflyer({
    'apiKey': api_key,
    'secret': api_secret,
})

#価格を保持・更新する配列
price_queue = deque(maxlen=120)

#BTC/JPYの最新価格を取得
def fetch_price(symbol='BTC/JPY'):
    ticker = exchange.fetch_ticker(symbol)
    return ticker['last']

#指値注文を発注する関数
def place_limit_order(symbol, side, price, amount):
    params = {
        'symbol': symbol,
        'side': side,
        'price': int(price),
        'amount': amount,
        'type': 'limit',
    }
    response = exchange.create_order(**params)
    return response

#注文キャンセル関数
def cancel_order(order_id, symbol='BTC/JPY'):
    exchange.cancel_order(order_id, symbol)

async def main_loop():
    while True:
        price = fetch_price()
        price_queue.append(price)

        highest_price = max(price_queue)
        print(f"The highest price in the last 2 hours is: {highest_price}")

        limit_price = highest_price * 0.9

        symbol = 'BTC/JPY'
        side = 'buy'
        amount = 0.001

        # Fetch open orders
        open_orders = exchange.fetch_open_orders(symbol)
        pprint(open_orders)

        # Cancel open orders
        for order in open_orders:
            cancel_order(order['id'], symbol)

        # Place new limit order
        place_limit_order(symbol, side, limit_price, amount)

        await asyncio.sleep(60)

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(main_loop())
except Exception as e:
    print(f"エラーが発生しました: {e}")

