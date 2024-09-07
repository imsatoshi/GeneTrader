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

    # 调整 ROI，可能需要更保守一些
    minimal_roi = {
        "0": 0.05,
        "30": 0.04,
        "60": 0.03,
        "120": 0.02
    }

    # 调整止损，现货通常可以设置更宽松一些
    stoploss = -0.15

    # 时间框架层级
    timeframe_hierarchy = {
        '1m': '5m',
        '5m': '15m',
        '15m': '1h',
        '1h': '4h',
        '4h': '1d',
        '1d': '1w',
        '1w': '1M'
    }

    # 订单类型设置
    order_types = {
        'entry': 'market',
        'exit': 'market',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    use_exit_signal = True
    exit_profit_only = False

    # 追踪止损设置
    trailing_stop = True
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.003
    trailing_stop_positive_offset = 0.008

    # 其他变量初始化
    dca_attempts = {}
    position_adjustment_enable = True
    candle_open_prices = {}
    last_dca_candle_index = {}

    last_dca_price = {}
    csl = {}
    commands = []
    initial_entry_ratio = DecimalParameter(0.4, 1.0, default=0.25, space='buy', optimize=True)

    new_sl_coef = DecimalParameter(0.3, 0.9, default=0.75, space='sell', optimize=False)

    # TTF 参数
    lookback_length = IntParameter(1, 30, default=15, space='buy', optimize=True)
    upper_trigger_level = IntParameter(1, 300, default=100, space='buy', optimize=True)
    lower_trigger_level = IntParameter(-300, -1, default=-100, space='buy', optimize=True)

    # 可优化参数
    buy_rsi = IntParameter(25, 60, default=55, space='buy', optimize=False)
    sell_rsi = IntParameter(50, 70, default=70, space='sell', optimize=False)

    # 基于ATR的止损参数
    atr_multiplier = DecimalParameter(1.0, 3.0, default=1.5, space='stoploss', optimize=False)

    # SWINGS 参数
    swing_window = IntParameter(10, 50, default=50, space='buy', optimize=False)
    swing_min_periods = IntParameter(1, 10, default=10, space='buy', optimize=False)
    swing_buffer = DecimalParameter(0.01, 0.1, default=0.03, space='buy', optimize=False)

    # 买入和卖出的MACD和EMA参数
    buy_macd = DecimalParameter(-0.02, 0.02, default=0.00, space='buy', optimize=False)
    buy_ema_short = IntParameter(5, 50, default=10, space='buy', optimize=False)
    buy_ema_long = IntParameter(50, 200, default=50, space='buy', optimize=False)

    sell_macd = DecimalParameter(-0.02, 0.02, default=-0.005, space='sell', optimize=False)
    sell_ema_short = IntParameter(5, 50, default=10, space='sell', optimize=False)
    sell_ema_long = IntParameter(50, 200, default=50, space='sell', optimize=False)

    # DCA相关参数
    volume_dca_int = IntParameter(1, 30, default=7, space='buy', optimize=False)
    a_vol_coef = DecimalParameter(1, 2, default=1, space='buy', optimize=False)
    dca_candles_modulo = IntParameter(1, 100, default=10, space='buy', optimize=True)
    dca_threshold = DecimalParameter(0.01, 0.5, default=0.01, space='buy', optimize=False)

    dca_multiplier = DecimalParameter(1.0, 2.0, default=1.5, space='buy', optimize=True)
    max_dca_orders = IntParameter(1, 5, default=3, space='buy', optimize=True)
    dca_profit_threshold = DecimalParameter(-0.20, -0.05, default=-0.10, space='buy', optimize=True)

    def __init__(self, config):
        return super().__init__(config)

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: Optional[float], max_stake: float,
                            entry_tag: Optional[str], side: str,
                            **kwargs) -> float:
        # 计算可用于此次交易的最大金额
        available_balance = self.wallets.get_available_stake_amount()
        max_stake_for_trade = available_balance * self.initial_entry_ratio.value

        # 确保留有足够的资金进行DCA
        stake_amount = min(proposed_stake, max_stake_for_trade)
        return stake_amount

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 计算各种技术指标
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['ema_short'] = ta.EMA(dataframe, timeperiod=self.buy_ema_short.value)
        dataframe['ema_long'] = ta.EMA(dataframe, timeperiod=self.buy_ema_long.value)
        dataframe['previous_close'] = dataframe['close'].shift(1)
        dataframe['max_since_buy'] = dataframe['high'].cummax()
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)

        # 计算枢轴点和阻力/支撑位
        pp, r1, s1 = self.calculate_pivots(dataframe)
        dataframe['pivot_point'] = pp
        dataframe['resistance_1'] = r1
        dataframe['support_1'] = s1

        swing_low, swing_high = self.calculate_swing(dataframe)
        dataframe['swing_low'] = swing_low
        dataframe['swing_high'] = swing_high

        # 添加阻力信号（例如，价格接近或突破R1）
        dataframe['resistance_signal'] = ((dataframe['close'] > dataframe['resistance_1']) & (
                dataframe['close'] > dataframe['previous_close']))

        # 计算布林带
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']

        # 计算最高和最低价
        dataframe['hh'] = dataframe['close'].rolling(window=self.lookback_length.value).max()
        dataframe['ll'] = dataframe['close'].rolling(window=self.lookback_length.value).min()

        # 计算买入和卖出力量
        dataframe['buyPower'] = dataframe['hh'] - dataframe['ll'].shift(self.lookback_length.value)
        dataframe['sellPower'] = dataframe['hh'].shift(self.lookback_length.value) - dataframe['ll']

        # 计算TTF
        dataframe['ttf'] = 200 * (dataframe['buyPower'] - dataframe['sellPower']) / (
                dataframe['buyPower'] + dataframe['sellPower'])

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 检查是否有手动触发的买入命令
        if len(self.commands) > 0:
            pair = self.commands[-1]['pair']
            if pair == metadata['pair']:
                command = self.commands[-1]['command']
                if command == 'BUY':
                    self.commands = [s for s in self.commands if s['pair'] != pair]
                    dataframe.loc[(dataframe['volume'] > 0), ['enter_long', 'enter_tag']] = (1, 'trigger_buy')
                    return dataframe

        # 买入条件列表
        conditions = [
            # 基本条件：MACD交叉和EMA交叉
            (dataframe['macd'] > dataframe['macdsignal']) & (dataframe['ema_short'] > dataframe['ema_long']) |
            (dataframe['resistance_signal']) & (dataframe['volume'] > 0) |
            (dataframe['ttf'] > self.upper_trigger_level.value)
        ]

        # 获取更高时间框架的数据进行多时间框架分析
        level = self.timeframe_hierarchy[self.timeframe]
        informative = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=level)

        if not informative.empty:
            # 确保'informative'与主dataframe对齐
            informative = informative.reindex(dataframe.index, method='nearest')
            # 现在可以安全地比较收盘价，因为它们已对齐
            conditions.append(dataframe['close'] < informative['close'].shift(1))
        else:
            logging.info(f"在'{level}'时间框架中没有{metadata['pair']}的可用数据。跳过此条件。")

        # 检查所有条件是否都是pandas Series，并应用逻辑AND归约以获得最终条件
        if all(isinstance(cond, pd.Series) for cond in conditions):
            final_condition = np.logical_and.reduce(conditions)
            dataframe.loc[final_condition, ['enter_long', 'enter_tag']] = (1, 'multi_timeframe_cross')
        else:
            logging.error("不是所有条件都是pandas Series。")

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 检查是否有手动触发的卖出命令
        if len(self.commands) > 0:
            pair = self.commands[-1]['pair']
            if pair == metadata['pair']:
                command = self.commands[-1]['command']
                if command == 'SELL':
                    self.commands = [s for s in self.commands if s['pair'] != pair]
                    dataframe.loc[(dataframe['volume'] > 0), ['exit_long', 'exit_tag']] = (1, 'trigger_sell')
                    return dataframe

        # 准备卖出条件
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
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

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
        if sl is not None and current_rate <= sl:
            return f"custom_stop_loss_{sl}"
        return None

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
        
        # 获取当前交易的DCA次数
        filled_entries = trade.select_filled_orders(trade.entry_side)
        count_of_entries = len(filled_entries)
        
        # 如果已经达到最大DCA次数，不再进行DCA
        if count_of_entries >= self.max_dca_orders.value:
            return None

        # 检查是否满足DCA条件
        if current_profit <= self.dca_profit_threshold.value:
            # 计算新的仓位大小
            stake_amount = trade.stake_amount * self.dca_multiplier.value
            
            # 确保新的仓位不超过最大允许仓位
            stake_amount = min(stake_amount, max_stake)
            
            # 获取当前的dataframe
            dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
            last_candle = dataframe.iloc[-1]
            
            # 额外的DCA条件检查
            if (last_candle['rsi'] < 30 and  # RSI 过低，可能是超卖
                last_candle['close'] < last_candle['bb_lowerband']):  # 价格低于布林带下轨
                
                # 记录DCA操作
                self.log_dca_event(trade, stake_amount, current_rate, current_profit)
                
                return stake_amount

        return None

    def log_dca_event(self, trade: Trade, stake_amount: float, current_rate: float, current_profit: float):
        """记录DCA事件"""
        logging.info(f"DCA triggered for {trade.pair}")
        logging.info(f"Current profit: {current_profit:.2%}")
        logging.info(f"Adding stake amount: {stake_amount}")
        logging.info(f"Current rate: {current_rate}")

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                        time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                        side: str, **kwargs) -> bool:
    
        # 获取当前的dataframe
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        # 计算整个dataframe的成交量均值
        volume_mean = dataframe['volume'].rolling(window=24).mean()
        
        # 获取最后一根蜡烛的数据
        last_candle = dataframe.iloc[-1]
        
        # 检查市场条件是否适合入场
        if (last_candle['volume'] > volume_mean.iloc[-1] and  # 最后一根蜡烛的成交量高于24小时平均
            last_candle['close'] > last_candle['ema_long']):  # 价格高于长期均线
            return True
        
        return False

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

    def calculate_swing(self, dataframe: DataFrame) -> Tuple[Series, Series]:
        swing_low = dataframe['low'].rolling(window=self.swing_window.value, min_periods=self.swing_min_periods.value).min()
        swing_high = dataframe['high'].rolling(window=self.swing_window.value, min_periods=self.swing_min_periods.value).max()
        return swing_low, swing_high

    def calculate_pivots(self, dataframe: DataFrame) -> Tuple[Series, Series, Series]:
        pivot_point = (dataframe['high'] + dataframe['low'] + dataframe['close']) / 3
        resistance_1 = 2 * pivot_point - dataframe['low']
        support_1 = 2 * pivot_point - dataframe['high']
        return pivot_point, resistance_1, support_1
