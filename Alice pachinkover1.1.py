import ccxt
import asyncio
import datetime

# BitflyerのAPIキーとシークレットキーを設定
api_key = ''
api_secret = ''

# Bitflyerのインスタンスを作成
exchange = ccxt.bitflyer({
    'apiKey': api_key,
    'secret': api_secret,
})

# 資産情報を取得する関数
async def get_asset_info():
    try:
        return await exchange.fetch_balance()
    except Exception as e:
        print("Failed to get asset info:", e)
        return None

# 注文をキャンセルする関数
async def cancel_all_orders():
    try:
        await exchange.cancel_all_orders()
        print("All orders cancelled successfully.")
    except Exception as e:
        print("Failed to cancel all orders:", e)

# 決済注文を発注する関数
async def place_exit_order(asset_info):
    try:
        # 直近120分の安値を取得
        candles = await exchange.fetch_ohlcv('BTC/JPY', timeframe='1m', limit=120)
        low_prices = [candle[3] for candle in candles]
        lowest_price = min(low_prices)

        # 10%上昇した価格を計算
        exit_price = lowest_price * (1 + 0.1)

        # 決済指値の執行注文
        order = await exchange.create_limit_order('BTC/JPY', 'sell', asset_info['free']['BTC'], exit_price)

        # 注文の実行
        await exchange.create_order(order['symbol'], order['type'], order['side'], order['amount'], order['price'])

        print("Exit order placed successfully.")
    except Exception as e:
        print("Failed to place exit order:", e)

# 建て玉を保有しているかどうかを判定する関数
def has_long_position(asset_info):
    if asset_info and 'BTC' in asset_info['free']:
        return True
    else:
        return False

# メインのトレードロジック
async def trade_logic():
    # レバレッジ倍率と証拠金を設定
    leverage = 2
    initial_margin = 10000  # 証拠金

    # N分間の高値とR%の価格下落を設定
    minutes = 120
    price_drop_percentage = 0.1

    while True:
        # 現在の時刻を取得
        current_time = datetime.datetime.now()

        # 注文解消時間（毎時間0分）に指値を解消
        if current_time.minute == 0:
            # 既存の注文を解消する処理
            await cancel_all_orders()

            # 資産情報を非同期に取得
            asset_info = await get_asset_info()

            # Longの建て玉を保有している場合は決済注文を発注
            if has_long_position(asset_info):
                await place_exit_order(asset_info)
            else:
                # 過去のデータを取得
                candles = await exchange.fetch_ohlcv('BTC/JPY', timeframe='1m', limit=minutes)

                # N分間の高値を取得
                high_price = [candle[2] for candle in candles]
                highest_price = max(high_price)

                # エントリー価格を計算
                entry_price = highest_price * (1 - price_drop_percentage)

                # エントリー指値の執行注文
                order = await exchange.create_limit_order('BTC/JPY', 'buy', leverage * initial_margin / entry_price, entry_price)

                # 注文の実行
                await exchange.create_order(order['symbol'], order['type'], order['side'], order['amount'], order['price'])

        # 1分ごとにループを実行
        await asyncio.sleep(60)

# トレードロジックの実行
asyncio.run(trade_logic())
