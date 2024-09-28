import json
import logging
import os
import sys
from functools import reduce
from threading import Thread

import numpy
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame, Series
from typing import Optional, Union, List, Tuple

from pandas_ta import stdev

from freqtrade.enums import ExitCheckTuple
from freqtrade.persistence import Trade, Order, CustomDataWrapper
from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter, IStrategy, IntParameter,
                                informative)
import datetime
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
import pandas_ta as pta


class DailyBuyStrategy(IStrategy):
    INTERFACE_VERSION = 3

    # Minimal ROI designed for the strategy
    minimal_roi = {
        "0": 0.03
    }

    timeframe_hierarchy = {
        '1m': '5m',
        '5m': '15m',
        '15m': '1h',
        '1h': '4h',
        '4h': '1d',
        '1d': '1w',
        '1w': '1M'
    }

    order_types = {
        'entry': 'market',
        'exit': 'market',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    stoploss = -0.1  # 将止损设置为 -10%

    use_exit_signal = True
    exit_profit_only = False

    # 调整追踪止损设置
    trailing_stop = True
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02

    dca_attempts = {}
    position_adjustment_enable = True
    candle_open_prices = {}
    last_dca_candle_index = {}

    last_dca_price = {}
    csl = {}
    commands = []
    new_sl_coef = DecimalParameter(0.3, 0.9, default=0.75, space='sell', optimize=True)

    # TTF
    lookback_length = IntParameter(1, 30, default=15, space='buy', optimize=True)
    upper_trigger_level = IntParameter(1, 300, default=100, space='buy', optimize=True)
    lower_trigger_level = IntParameter(-300, -1, default=-100, space='buy', optimize=True)

    # Hyperoptable parameters
    buy_rsi = IntParameter(25, 60, default=55, space='buy', optimize=True)
    sell_rsi = IntParameter(50, 70, default=70, space='sell', optimize=True)

    # ATR based stop loss parameters
    atr_multiplier = DecimalParameter(1.0, 3.0, default=1.5, space='stoploss', optimize=True)

    # SWINGS
    swing_window = IntParameter(10, 50, default=50, space='buy', optimize=True)
    swing_min_periods = IntParameter(1, 10, default=10, space='buy', optimize=True)
    swing_buffer = DecimalParameter(0.01, 0.1, default=0.03, space='buy', optimize=True)

    buy_macd = DecimalParameter(-0.02, 0.02, default=0.00, space='buy', optimize=True)
    buy_ema_short = IntParameter(5, 50, default=10, space='buy', optimize=True)
    buy_ema_long = IntParameter(50, 200, default=50, space='buy', optimize=True)

    sell_macd = DecimalParameter(-0.02, 0.02, default=-0.005, space='sell', optimize=True)
    sell_ema_short = IntParameter(5, 50, default=10, space='sell', optimize=True)
    sell_ema_long = IntParameter(50, 200, default=50, space='sell', optimize=True)

    volume_dca_int = IntParameter(1, 30, default=7, space='buy', optimize=True)
    a_vol_coef = DecimalParameter(1, 2, default=1, space='buy', optimize=True)
    dca_candles_modulo = IntParameter(1, 100, default=10, space='buy', optimize=True)
    dca_threshold = DecimalParameter(0.01, 0.5, default=0.01, space='buy', optimize=True)

    def __init__(self, config):
        return super().__init__(config)

    def calculate_swing(self, dataframe):
        swing_low = pd.Series(
            dataframe['low'].rolling(window=self.swing_window.value, min_periods=self.swing_min_periods.value).min(),
            index=dataframe.index
        )
        swing_high = pd.Series(
            dataframe['high'].rolling(window=self.swing_window.value, min_periods=self.swing_min_periods.value).max(),
            index=dataframe.index
        )
        return swing_low, swing_high

    def calculate_pivots(self, dataframe: DataFrame) -> Tuple[Series, Series, Series]:
        # Calculate the pivot point (PP)
        dataframe['pp'] = (dataframe['high'].shift(1) + dataframe['low'].shift(1) + dataframe['close'].shift(1)) / 3
        # Calculate the first resistance (R1)
        dataframe['r1'] = 2 * dataframe['pp'] - dataframe['low'].shift(1)
        # Calculate the first support (S1)
        dataframe['s1'] = 2 * dataframe['pp'] - dataframe['high'].shift(1)
        return dataframe['pp'], dataframe['r1'], dataframe['s1']

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: Optional[float], max_stake: float,
                            entry_tag: Optional[str], side: str,
                            **kwargs) -> float:
        return proposed_stake / 4

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['ema_short'] = ta.EMA(dataframe, timeperiod=self.buy_ema_short.value)
        dataframe['ema_long'] = ta.EMA(dataframe, timeperiod=self.buy_ema_long.value)
        dataframe['previous_close'] = dataframe['close'].shift(1)
        dataframe['max_since_buy'] = dataframe['high'].cummax()
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)

        # Calculate Pivot Points and Resistance/Support Levels
        pp, r1, s1 = self.calculate_pivots(dataframe)
        dataframe['pivot_point'] = pp
        dataframe['resistance_1'] = r1
        dataframe['support_1'] = s1

        swing_low, swing_high = self.calculate_swing(dataframe)
        dataframe['swing_low'] = swing_low
        dataframe['swing_high'] = swing_high

        # Add a resistance signal (for example, price approaching or crossing R1)
        dataframe['resistance_signal'] = ((dataframe['close'] > dataframe['resistance_1']) & (
                dataframe['close'] > dataframe['previous_close']))

        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']
        # CustomDataWrapper.set_custom_data(trade_id=40, key='test', value='ahoj')
        # t = CustomDataWrapper.get_custom_data(trade_id=40, key='test')[0].value

        # Calculate highest and lowest
        dataframe['hh'] = dataframe['close'].rolling(window=self.lookback_length.value).max()
        dataframe['ll'] = dataframe['close'].rolling(window=self.lookback_length.value).min()

        # Calculate buy and sell power
        dataframe['buyPower'] = dataframe['hh'] - dataframe['ll'].shift(self.lookback_length.value)
        dataframe['sellPower'] = dataframe['hh'].shift(self.lookback_length.value) - dataframe['ll']

        # Calculate TTF
        dataframe['ttf'] = 200 * (dataframe['buyPower'] - dataframe['sellPower']) / (
                dataframe['buyPower'] + dataframe['sellPower'])

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if len(self.commands) > 0:
            pair = self.commands[-1]['pair']
            if pair == metadata['pair']:
                command = self.commands[-1]['command']
                if command == 'BUY':
                    self.commands = [s for s in self.commands if s['pair'] != pair]
                    dataframe.loc[(dataframe['volume'] > 0), ['enter_long', 'enter_tag']] = (1, 'trigger_buy')
                    return dataframe

        # Conditions list can be used to store various buying conditions
        conditions = [
            # Basic condition: MACD crossover and EMA crossover
            (dataframe['macd'] > dataframe['macdsignal']) & (dataframe['ema_short'] > dataframe['ema_long']) |
            (dataframe['resistance_signal']) & (dataframe['volume'] > 0) |
            (dataframe['ttf'] > self.upper_trigger_level.value)
        ]

        # Získání dat vyššího časového rámce pro analýzu na více časových rámcích
        level = self.timeframe_hierarchy[self.timeframe]
        informative = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=level)

        if not informative.empty:
            # Ujistěte se, že 'informative' je zarovnán s hlavním dataframe
            informative = informative.reindex(dataframe.index, method='nearest')
            # Nyní bezpečně porovnávejte uzavírací ceny, protože jsou zarovnané
            conditions.append(dataframe['close'] < informative['close'].shift(1))
        else:
            logging.info(f"No data available for {metadata['pair']} in '{level}' timeframe. Skipping this condition.")

        # Check if all conditions are pandas Series and apply logical AND reduction to get the final condition
        if all(isinstance(cond, pd.Series) for cond in conditions):
            final_condition = np.logical_and.reduce(conditions)
            dataframe.loc[final_condition, ['enter_long', 'enter_tag']] = (1, 'multi_timeframe_cross')
        else:
            logging.error("Not all conditions are pandas Series.")

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if len(self.commands) > 0:
            pair = self.commands[-1]['pair']
            if pair == metadata['pair']:
                command = self.commands[-1]['command']
                if command == 'SELL':
                    self.commands = [s for s in self.commands if s['pair'] != pair]
                    dataframe.loc[(dataframe['volume'] > 0), ['exit_long', 'exit_tag']] = (1, 'trigger_sell')
                    return dataframe

        # Příprava podmínek
        conditions = [
            (
                    (dataframe['close'] > dataframe['swing_high']) |
                    (
                            (dataframe['macd'] < dataframe['macdsignal']) &
                            (dataframe['ema_short'] < dataframe['ema_long'])
                    ) |
                    (dataframe['ttf'] < self.lower_trigger_level.value)
            ),
            (dataframe['volume'] > 0)
        ]
        exit_condition = np.logical_and.reduce([cond.values for cond in conditions if isinstance(cond, pd.Series)])
        dataframe.loc[exit_condition, ['exit_long', 'exit_tag']] = (1, 'macd_ema_exit')
        return dataframe

    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, amount: float,
                           rate: float, time_in_force: str, exit_reason: str,
                           current_time: datetime, **kwargs) -> bool:

        profit_ratio = trade.calc_profit_ratio(rate)

        if ('macd_ema_exit' in exit_reason) and (profit_ratio >= 0.005):
            return True

        if (('trailing' in exit_reason) or ('roi' in exit_reason)) and (profit_ratio >= 0.005):
            return True

        if 'force' in exit_reason or 'trigger' in exit_reason:
            return True

        return False

    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> Optional[Union[str, bool]]:
        sl = self.get_mk_sl(trade)
        if current_rate <= sl:
            return f"custom_stop_loss_{sl}"
        pass

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, timeframe) for pair in pairs for timeframe in self.timeframe_hierarchy.keys()]
        return informative_pairs

    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs) -> Optional[float]:

        dcas = self.get_dca_list(trade)
        if len(dcas) > 0 and current_rate >= (dcas[-1] * 0.995):
           return None

        if current_profit >= -self.dca_threshold.value:
            return None

        dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        if dataframe.empty:
            return None

        last_candle = dataframe.iloc[-1]
        last_index = dataframe.index[-1]

        dca_list = self.get_dca_list(trade)
        if dca_list and current_rate > dca_list[-1]:
            logging.info(
                f"Actual price {current_rate} is higher than last DCA price {dca_list[-1]}. DCA will not be applied.")
            return None

        if (last_index % self.dca_candles_modulo.value != 0):
            return None

        if last_candle['resistance_signal']:
            self.confirm_dca(current_rate, trade)
            logging.info(
                f"{current_time} - DCA triggered for {trade.pair}. Adjusting position with additional stake {trade.stake_amount}")
            return trade.stake_amount  # 现货策略中，通常DCA金额与初始投资相同

        return None

    def get_dca_list(self, trade):
        try:
            dcas = CustomDataWrapper.get_custom_data(trade_id=trade.id, key="DCA")[0].value
            return dcas
        except Exception as ex:
            pass
        return []

    def get_mk_sl(self, trade):
        try:
            sl = CustomDataWrapper.get_custom_data(trade_id=trade.id, key="SL")[0].value
            return sl
        except Exception as ex:
            pass
        return trade.stop_loss

    def set_mk_sl(self, trade, current_rate):
        sl = current_rate * self.new_sl_coef.value
        CustomDataWrapper.set_custom_data(trade_id=trade.id, key="SL", value=sl)

    def confirm_dca(self, current_rate, trade):
        dcas = self.get_dca_list(trade)
        dcas.append(current_rate)
        self.set_mk_sl(trade, current_rate)
        CustomDataWrapper.set_custom_data(trade_id=trade.id, key="DCA", value=dcas)