import ccxt
import asyncio
import datetime
import nest_asyncio
import math 
import ccxt.async_support as ccxt

# 非同期I/Oを使うためのセットアップ
nest_asyncio.apply()

# BitflyerのAPIキーとシークレットキーを設定
api_key = ''
api_secret = ''

# Bitflyerのインスタンスを作成
exchange = ccxt.bitflyer({
    'apiKey': api_key,
    'secret': api_secret,
})

# OHLCVを作成する関数
def build_ohlcv(trades, timeframe):
    # Change timestamp to datetime object for proper comparison
    sorted_trades = sorted(trades, key=lambda x: datetime.datetime.strptime(x['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ"))
    grouped_trades = []
    current_group = []
    current_timestamp = datetime.datetime.strptime(sorted_trades[0]['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ")
    for trade in sorted_trades:
        trade_time = datetime.datetime.strptime(trade['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ")
        if (trade_time - current_timestamp).seconds < timeframe * 60:
            current_group.append(trade)
        else:
            grouped_trades.append(current_group)
            current_group = [trade]
            current_timestamp = trade_time

    ohlcv_data = []
    for trades in grouped_trades:
        timestamps = [datetime.datetime.strptime(x['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ") for x in trades]
        prices = [x['price'] for x in trades]
        volumes = [x['amount'] for x in trades]
        ohlcv_data.append([
            min(timestamps),
            prices[0],
            max(prices),
            min(prices),
            prices[-1],
            sum(volumes)
        ])

    return ohlcv_data

# 約定履歴を取得する関数
async def fetch_executions(symbol='BTC/JPY', limit=1000):
    try:
        # Bitflyerのgetexecutionsエンドポイントを直接呼び出す
        executions = await exchange.private_get_getexecutions({
            'product_code': exchange.market_id(symbol),
            'count': limit,
        })

        # 約定履歴をTrade形式に変換
        trades = [{'timestamp': ex['exec_date'], 'price': ex['price'], 'amount': ex['size']} for ex in executions]
        return trades
    except Exception as e:
        # 約定履歴の取得に失敗した場合、エラーメッセージを出力
        print(f"Failed to fetch executions: {e}")
        return None

# 資産情報を取得する関数
async def get_asset_info():
    try:
        # 資産情報を取得
        return await exchange.fetch_balance()
    except Exception as e:
        # 資産情報の取得に失敗した場合、エラーメッセージを出力
        print(f"Failed to get asset info: {e}")
        return None

# 注文をキャンセルする関数
async def cancel_all_orders(symbol='BTC/JPY'):
    try:
        # 全ての注文情報を取得
        open_orders = await exchange.fetch_open_orders(symbol)
        # 各注文についてキャンセルを行う
        for order in open_orders:
            await exchange.cancel_order(order['id'], symbol)
        print("All orders cancelled successfully.")
    except Exception as e:
        # 注文のキャンセルに失敗した場合、エラーメッセージを出力
        print(f"Failed to cancel all orders: {e}")
        return None

# 決済注文を発注する関数
async def place_exit_order(asset_info, ohlcv, symbol='BTC/JPY'):
    try:
        # 直近のOHLCVデータを取得
        last_candle = ohlcv[-1]
        low_prices = [candle[3] for candle in ohlcv]
        lowest_price = min(low_prices)

        # 10%上昇した価格を計算
        exit_price = lowest_price * (1 + 0.1)

        # 決済指値の執行注文
        await exchange.create_limit_order(symbol, 'sell', asset_info['free']['BTC'], exit_price)

        print("Exit order placed successfully.")
    except Exception as e:
        # 決済注文の発注に失敗した場合、エラーメッセージを出力
        print(f"Failed to place exit order: {e}")

# 建て玉を保有しているかどうかを判定する関数
def has_long_position(asset_info):
    # 資産情報が存在し、BTCの保有量がある場合はTrueを返す
    return asset_info and 'BTC' in asset_info['free']

# メインのトレードロジック
async def trade_logic(minutes=120, price_drop_percentage=0.1):
    while True:
        current_time = datetime.datetime.now()

        if current_time.minute == 0:
            await cancel_all_orders()

            asset_info = await get_asset_info()

            if has_long_position(asset_info):
                trades = await fetch_executions()
                ohlcv = build_ohlcv(trades, timeframe=1)

                await place_exit_order(asset_info, ohlcv)
            else:
                if asset_info and 'JPY' in asset_info['free']:
                    free_jpy = asset_info['free']['JPY']
                    if free_jpy <= 0:
                        print("Insufficient margin. Please deposit funds.")
                        await asyncio.sleep(60)
                        continue

                trades = await fetch_executions()
                ohlcv = build_ohlcv(trades, timeframe=1)

                candles = await exchange.fetch_ohlcv('BTC/JPY', timeframe='1m', limit=minutes)

                high_price = [candle[2] for candle in candles]
                highest_price = max(high_price)

                entry_price = highest_price * (1 - price_drop_percentage)

                symbol = 'BTC/JPY'
                amount = free_jpy / entry_price
                amount = math.floor(amount * 1000) / 1000

                await exchange.create_limit_order(symbol, 'buy', amount, entry_price)

                print("Entry order placed successfully.")

        await asyncio.sleep(60)

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(trade_logic())
finally:
    loop.run_until_complete(exchange.close())
