import pandas as pd
import numpy as np
import ccxt
from itertools import product

class RSIWILLRStrategy:
    def __init__(self, rsi_buy_threshold=30, rsi_sell_threshold=70, willr_buy_threshold=-80, willr_sell_threshold=-20, stoploss=-0.10):
        self.rsi_buy_threshold = rsi_buy_threshold
        self.rsi_sell_threshold = rsi_sell_threshold
        self.willr_buy_threshold = willr_buy_threshold
        self.willr_sell_threshold = willr_sell_threshold
        self.stoploss = stoploss
        self.timeframe = '30m'

    def calculate_rsi(self, series, period=14):
        delta = series.diff(1)
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_willr(self, dataframe, period=14):
        high = dataframe['high'].rolling(window=period).max()
        low = dataframe['low'].rolling(window=period).min()
        willr = -100 * ((high - dataframe['close']) / (high - low))
        return willr

    def populate_indicators(self, dataframe):
        dataframe['rsi'] = self.calculate_rsi(dataframe['close'])
        dataframe['willr'] = self.calculate_willr(dataframe)
        return dataframe

    def generate_signals(self, dataframe):
        dataframe['buy'] = (
            (dataframe['rsi'] < self.rsi_buy_threshold) &
            (dataframe['willr'] < self.willr_buy_threshold)
        ).astype(int)

        dataframe['sell'] = (
            (dataframe['rsi'] > self.rsi_sell_threshold) &
            (dataframe['willr'] > self.willr_sell_threshold)
        ).astype(int)
        return dataframe

    def simulate_trading(self, dataframe):
        dataframe = self.populate_indicators(dataframe)
        dataframe = self.generate_signals(dataframe)

        initial_balance = 500
        balance = initial_balance
        position = 0  # 1 if holding asset, 0 if not
        entry_price = 0
        cumulative_profit = 0
        trades = []
        drawdown = []
        equity_curve = [balance]

        for index, row in dataframe.iterrows():
            if row['buy'] == 1 and position == 0:
                entry_price = row['close']
                position = 1
                trades.append({'entry_price': entry_price, 'exit_price': None, 'profit': None})
                print(f"Buying at {entry_price}")
            elif row['sell'] == 1 and position == 1:
                exit_price = row['close']
                profit = (exit_price - entry_price) / entry_price * balance
                balance += profit
                cumulative_profit += profit
                trades[-1]['exit_price'] = exit_price
                trades[-1]['profit'] = profit
                drawdown.append(balance)
                equity_curve.append(balance)
                position = 0
                print(f"Selling at {exit_price} | Profit: {profit}")

            # Implement stop-loss
            if position == 1 and (row['close'] - entry_price) / entry_price < self.stoploss:
                exit_price = row['close']
                profit = (exit_price - entry_price) / entry_price * balance
                balance += profit
                cumulative_profit += profit
                trades[-1]['exit_price'] = exit_price
                trades[-1]['profit'] = profit
                drawdown.append(balance)
                equity_curve.append(balance)
                position = 0
                print(f"Stop-Loss Triggered at {exit_price} | Loss: {profit}")

        if position == 1:
            final_price = dataframe.iloc[-1]['close']
            profit = (final_price - entry_price) / entry_price * balance
            balance += profit
            cumulative_profit += profit
            trades[-1]['exit_price'] = final_price
            trades[-1]['profit'] = profit
            print(f"Selling at {final_price} (final close) | Profit: {profit}")

        final_balance = balance
        num_trades = len([trade for trade in trades if trade['exit_price'] is not None])
        win_trades = len([trade for trade in trades if trade['profit'] and trade['profit'] > 0])
        win_rate = win_trades / num_trades * 100 if num_trades > 0 else 0
        max_drawdown = np.max(np.maximum.accumulate(drawdown) - drawdown) if drawdown else 0

        metrics = {
            'cumulative_profit': cumulative_profit,
            'num_trades': num_trades,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'final_balance': final_balance,
            'equity_curve': equity_curve
        }
        return metrics

def fetch_ohlcv(symbol='BTC/USDT', timeframe='30m', since=None, limit=336):
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
    dataframe = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    dataframe['timestamp'] = pd.to_datetime(dataframe['timestamp'], unit='ms')
    dataframe.set_index('timestamp', inplace=True)
    return dataframe

def manual_hyperopt():
    dataframe = fetch_ohlcv()

    best_cumulative_profit = -np.inf
    best_metrics = {}
    best_params = None

    rsi_buy_range = range(5, 100, 5)
    rsi_sell_range = range(40, 100, 5)
    willr_buy_range = range(-100, 0, 5)
    willr_sell_range = range(-100, 0, 5)
    stoploss_range = np.arange(-0.30, -0.01, 0.01)  # Testing stop-loss from -30% to -1%

    for rsi_buy, rsi_sell, willr_buy, willr_sell, stoploss in product(rsi_buy_range, rsi_sell_range, willr_buy_range, willr_sell_range, stoploss_range):
        strategy = RSIWILLRStrategy(
            rsi_buy_threshold=rsi_buy, 
            rsi_sell_threshold=rsi_sell, 
            willr_buy_threshold=willr_buy, 
            willr_sell_threshold=willr_sell, 
            stoploss=stoploss
        )

        print(f"Testing with RSI Buy: {rsi_buy}, RSI Sell: {rsi_sell}, WILLR Buy: {willr_buy}, WILLR Sell: {willr_sell}, Stop-Loss: {stoploss}")
        metrics = strategy.simulate_trading(dataframe)

        print(f"Cumulative Profit: {metrics['cumulative_profit']}, Num Trades: {metrics['num_trades']}, Win Rate: {metrics['win_rate']}%, Max Drawdown: {metrics['max_drawdown']}")

        if metrics['cumulative_profit'] > best_cumulative_profit:
            best_cumulative_profit = metrics['cumulative_profit']
            best_metrics = metrics
            best_params = (rsi_buy, rsi_sell, willr_buy, willr_sell, stoploss)

    print("\nBest parameters:")
    print(f"RSI Buy: {best_params[0]}, RSI Sell: {best_params[1]}, WILLR Buy: {best_params[2]}, WILLR Sell: {best_params[3]}, Stop-Loss: {best_params[4]}")
    print(f"Best Cumulative Profit: {best_metrics['cumulative_profit']}")
    print(f"Number of Trades: {best_metrics['num_trades']}")
    print(f"Win Rate: {best_metrics['win_rate']}%")
    print(f"Max Drawdown: {best_metrics['max_drawdown']}")
    print(f"Final Balance: {best_metrics['final_balance']}")

if __name__ == "__main__":
    manual_hyperopt()