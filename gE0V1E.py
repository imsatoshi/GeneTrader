from datetime import datetime, timedelta
import talib.abstract as ta
import pandas_ta as pta
from freqtrade.persistence import Trade
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
from freqtrade.strategy import DecimalParameter, IntParameter
from functools import reduce
import warnings
from typing import Optional
import logging

warnings.simplefilter(action="ignore", category=RuntimeWarning)
TMP_HOLD = []
TMP_HOLD1 = []


class gE0V1E(IStrategy):
    minimal_roi = {
        "0": 1
    }
    timeframe = '5m'
    process_only_new_candles = True
    startup_candle_count = 240
    order_types = {
        'entry': 'market',
        'exit': 'market',
        'emergency_exit': 'market',
        'force_entry': 'market',
        'force_exit': "market",
        'stoploss': 'market',
        'stoploss_on_exchange': False,
        'stoploss_on_exchange_interval': 60,
        'stoploss_on_exchange_market_ratio': 0.99
    }
    position_adjustment_enable = True
    max_entry_position_adjustment = 3

    # stoploss = -0.25
    stoploss_opt = DecimalParameter(-0.5, -0.1, default=-0.44, decimals=2, space='sell', optimize=True)
    stoploss = stoploss_opt.value

    trailing_stop = True
    # trailing_stop_positive = 0.003
    # trailing_stop_positive_offset = 0.03

    trailing_stop_positive_opt = DecimalParameter(0.001, 0.01, default=0.001, decimals=3, space='sell', optimize=True)
    trailing_stop_positive = trailing_stop_positive_opt.value

    trailing_stop_positive_offset_opt = DecimalParameter(0.02, 0.1, default=0.02, decimals=2, space='sell', optimize=True)

    # 确保 trailing_stop_positive_offset 始终大于 trailing_stop_positive
    def trailing_stop_positive_offset_guard(self):
        return max(self.trailing_stop_positive + 0.01, self.trailing_stop_positive_offset_opt.value)

    trailing_stop_positive_offset = property(trailing_stop_positive_offset_guard)

    trailing_only_offset_is_reached = True
    buy_rsi_fast_32 = IntParameter(20, 70, default=38, space='buy', optimize=True)
    buy_rsi_32 = IntParameter(15, 50, default=42, space='buy', optimize=True)
    buy_sma15_32 = DecimalParameter(0.900, 1, default=0.965, decimals=3, space='buy', optimize=True)
    buy_cti_32 = DecimalParameter(-1, 1, default=1.0, decimals=2, space='buy', optimize=True)

    sell_fastx = IntParameter(50, 100, default=68, space='sell', optimize=True)
    sell_loss_cci = IntParameter(0, 600, default=443, space='sell', optimize=True)
    sell_loss_cci_profit = DecimalParameter(-0.15, 0, default=-0.15, decimals=2, space='sell', optimize=True)
    
    custom_sell_cci = IntParameter(0, 600, default=577, space='sell', optimize=True)
    custom_sell_cci_profit = DecimalParameter(-0.25, 0, default=-0.07, decimals=2, space='sell', optimize=True)

    custom_current_profit = DecimalParameter(0.0, 0.05, default=0.01, decimals=2, space='sell', optimize=True)
    stop_duration_candles = IntParameter(12, 96, default=83, space='sell', optimize=True)

    buy_new_rsi_fast = IntParameter(30, 50, default=37, space='buy', optimize=True)
    buy_new_rsi = IntParameter(20, 40, default=32, space='buy', optimize=True)
    low_min_profit = DecimalParameter(-0.4, -0.1, default=-0.1, decimals=2, space='sell', optimize=True)
    high_min_profit = DecimalParameter(-0.1, 0, default=-0.1, decimals=2, space='sell', optimize=True)
    hold_time = IntParameter(8, 48, default=40, space='sell', optimize=True)

    # 简化 grind 模式相关的参数
    grinding_enable = True
    # grind_1_stop_grinds = -0.30
    grind_1_stop_grinds_opt = DecimalParameter(-0.5, -0.1, default=-0.30, decimals=2, space='sell', optimize=True)

    # grind_1_profit_threshold = 0.018
    grind_1_profit_threshold_opt = DecimalParameter(0.01, 0.05, default=0.018, decimals=3, space='sell', optimize=True)

    grind_1_stakes_1 = DecimalParameter(0.50, 2, default=1.0, decimals=2, space='sell', optimize=True)
    grind_1_stakes_2 = DecimalParameter(0.50, 2, default=1.0, decimals=2, space='sell', optimize=True)
    grind_1_stakes_3 = DecimalParameter(0.50, 2, default=1.0, decimals=2, space='sell', optimize=True)
    grind_1_stakes = [grind_1_stakes_1.value, grind_1_stakes_2.value, grind_1_stakes_3.value]

    grind_1_sub_thresholds_1 = DecimalParameter(-0.065, -0.01, default=-0.025, decimals=3, space='sell', optimize=True)
    grind_1_sub_thresholds_2 = DecimalParameter(-0.075, -0.01, default=-0.025, decimals=3, space='sell', optimize=True)
    grind_1_sub_thresholds_3 = DecimalParameter(-0.085, -0.01, default=-0.025, decimals=3, space='sell', optimize=True)

    # grind_1_sub_thresholds = [-0.035, -0.045, -0.055]
    grind_1_sub_thresholds = [grind_1_sub_thresholds_1.value, grind_1_sub_thresholds_2.value, grind_1_sub_thresholds_3.value]

    sma_ratio = DecimalParameter(0.900, 1, default=0.965, decimals=3, space='buy', optimize=True)

    # 扩大适用的标签范围
    long_grind_mode_tags = ["120", "buy_1", "buy_new"]  # 添加更多适用的标签
    short_grind_mode_tags = ["620", "sell_1", "sell_new"]  # 添加更多适用的标签

    @property
    def protections(self):
        return [
        {
            "method": "CooldownPeriod",
            "stop_duration_candles": self.stop_duration_candles.value
        }
        ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # buy_1 indicators
        dataframe['sma_15'] = ta.SMA(dataframe, timeperiod=15)
        dataframe['cti'] = pta.cti(dataframe["close"], length=20)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_fast'] = ta.RSI(dataframe, timeperiod=4)
        dataframe['rsi_slow'] = ta.RSI(dataframe, timeperiod=20)
        # profit sell indicators
        stoch_fast = ta.STOCHF(dataframe, 5, 3, 0, 3, 0)
        dataframe['fastk'] = stoch_fast['fastk']

        dataframe['cci'] = ta.CCI(dataframe, timeperiod=20)

        dataframe['ma120'] = ta.MA(dataframe, timeperiod=120)
        dataframe['ma240'] = ta.MA(dataframe, timeperiod=240)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        dataframe.loc[:, 'enter_tag'] = ''
        buy_1 = (
                (dataframe['rsi_slow'] < dataframe['rsi_slow'].shift(1)) &
                (dataframe['rsi_fast'] < self.buy_rsi_fast_32.value) &
                (dataframe['rsi'] > self.buy_rsi_32.value) &
                (dataframe['close'] < dataframe['sma_15'] * self.buy_sma15_32.value) &
                (dataframe['cti'] < self.buy_cti_32.value)
        )

        buy_new = (
                (dataframe['rsi_slow'] < dataframe['rsi_slow'].shift(1)) &
                (dataframe['rsi_fast'] < self.buy_new_rsi_fast.value) &
                (dataframe['rsi'] > self.buy_new_rsi.value) &
                (dataframe['close'] < dataframe['sma_15'] * self.sma_ratio.value) &
                (dataframe['cti'] < self.buy_cti_32.value)
        )

        conditions.append(buy_1)
        dataframe.loc[buy_1, 'enter_tag'] += 'buy_1'

        conditions.append(buy_new)
        dataframe.loc[buy_new, 'enter_tag'] += 'buy_new'

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x | y, conditions),
                'enter_long'] = 1
        return dataframe

    def custom_exit(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float,
                    current_profit: float, **kwargs):
        dataframe, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        current_candle = dataframe.iloc[-1].squeeze()

        min_profit = trade.calc_profit_ratio(trade.min_rate)

        if current_candle['close'] > current_candle["ma120"] or current_candle['close'] > current_candle["ma240"]:
            if trade.id not in TMP_HOLD:
                TMP_HOLD.append(trade.id)
        else:
            if trade.id not in TMP_HOLD1:
                TMP_HOLD1.append(trade.id)

        if current_profit > self.custom_current_profit.value:
            if current_candle["fastk"] > self.sell_fastx.value:
                return "fastk_profit_sell"

        if current_candle["cci"] > self.custom_sell_cci.value:
            if current_candle["high"] >= trade.open_rate:
                return "cci_high_sell"
            
        if min_profit <= self.custom_sell_cci_profit.value:
            if current_profit > self.sell_loss_cci_profit.value:
                if current_candle["cci"] > self.sell_loss_cci.value:
                    return "cci_loss_sell"

        if trade.id in TMP_HOLD and current_candle["close"] < current_candle["ma120"] and current_candle["close"] < \
                current_candle["ma240"]:
            if current_time - timedelta(minutes=self.hold_time.value) > trade.open_date_utc:
                TMP_HOLD.remove(trade.id)
                return "ma120_sell"

        if trade.id in TMP_HOLD1:
            if current_candle["high"] > current_candle["ma120"] or current_candle["high"] > current_candle["ma240"]:
                if self.low_min_profit.value <= min_profit <= self.high_min_profit.value:
                    TMP_HOLD1.remove(trade.id)
                    return "cross_120_or_240_sell"

        return None



    def exit_grind(self, trade: "Trade", current_profit: float, grind_mode: str):
        filled_entries = trade.select_filled_orders(trade.entry_side)
        count_of_entries = len(filled_entries)

        if count_of_entries == 1:
            stake_amount = filled_entries[0].cost
            slice_amount = stake_amount / 4
            slice_profit = slice_amount * self.grind_1_profit_threshold_opt.value

            if current_profit > 0 and current_profit > slice_profit:
                return True, f"exit_{grind_mode}_grind_profit"

        if current_profit > 0.018:
            return True, f"exit_{grind_mode}_grind_big_profit"

        if current_profit <= self.grind_1_stop_grinds_opt.value:
            return True, f"exit_{grind_mode}_grind_stop_loss"

        return False, None

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, ['exit_long', 'exit_tag']] = (0, 'long_out')
        return dataframe

    def adjust_entry_price(self, trade: Trade, current_time: datetime, current_rate: float, current_entry_rate: float, current_entry_profit: float, **kwargs):
        return current_entry_rate

    # 在adjust_trade_position方法中添加grind模式的逻辑
    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs) -> Optional[float]:
        
        dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
        previous_candle = dataframe.iloc[-2].squeeze()

        if not self.grinding_enable:
            logging.info(f"DCA disabled for {trade.pair}, skipping adjust_trade_position")
            return None

        # 检查是否满足 re-entry 条件
        buy_1_condition = (
            (last_candle['rsi_slow'] < previous_candle['rsi_slow']) and
            (last_candle['rsi_fast'] < self.buy_rsi_fast_32.value) and
            (last_candle['rsi'] > self.buy_rsi_32.value) and
            (last_candle['close'] < last_candle['sma_15'] * self.buy_sma15_32.value) and
            (last_candle['cti'] < self.buy_cti_32.value)
        )

        buy_new_condition = (
            (last_candle['rsi_slow'] < previous_candle['rsi_slow']) and
            (last_candle['rsi_fast'] < self.buy_new_rsi_fast.value) and
            (last_candle['rsi'] > self.buy_new_rsi.value) and
            (last_candle['close'] < last_candle['sma_15'] * self.sma_ratio.value) and
            (last_candle['cti'] < self.buy_cti_32.value)
        )

        if not (buy_1_condition or buy_new_condition):
            return None

        filled_entries = trade.select_filled_orders(trade.entry_side)
        count_of_entries = len(filled_entries)

        if count_of_entries < len(self.grind_1_stakes):
            initial_stake = filled_entries[0].cost
            dca_stake = initial_stake * self.grind_1_stakes[count_of_entries]

            # 检查是否达到 DCA 阈值
            if current_profit <= self.grind_1_sub_thresholds[count_of_entries]:
                adjusted_stake = max(min(dca_stake, max_stake), min_stake)
                logging.info(f"Performing DCA for {trade.pair}: stake={adjusted_stake:.4f}")
                return adjusted_stake

        return None



