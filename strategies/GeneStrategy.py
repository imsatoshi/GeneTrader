import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
from functools import reduce
import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import merge_informative_pair, DecimalParameter, stoploss_from_open, RealParameter,IntParameter,informative
from pandas import DataFrame, Series
from datetime import datetime
import math
import logging
from freqtrade.persistence import Trade
import pandas_ta as pta
from technical.indicators import RMI

logger = logging.getLogger(__name__)

# Elliot Wave Oscillator
def ewo(dataframe, sma1_length=5, sma2_length=35):
    sma1 = ta.EMA(dataframe, timeperiod=sma1_length)
    sma2 = ta.EMA(dataframe, timeperiod=sma2_length)
    smadif = (sma1 - sma2) / dataframe['close'] * 100
    return smadif



def top_percent_change_dca(dataframe: DataFrame, length: int) -> float:
        """
        Percentage change of the current close from the range maximum Open price

        :param dataframe: DataFrame The original OHLC dataframe
        :param length: int The length to look back
        """
        if length == 0:
            return (dataframe['open'] - dataframe['close']) / dataframe['close']
        else:
            return (dataframe['open'].rolling(length).max() - dataframe['close']) / dataframe['close']
        
#EWO

def EWO(dataframe, ema_length=5, ema2_length=3):
    df = dataframe.copy()
    ema1 = ta.EMA(df, timeperiod=ema_length)
    ema2 = ta.EMA(df, timeperiod=ema2_length)
    emadif = (ema1 - ema2) / df['close'] * 100
    return emadif

# Williams %R
def williams_r(dataframe: DataFrame, period: int = 14) -> Series:
    """Williams %R, or just %R, is a technical analysis oscillator showing the current closing price in relation to the high and low
        of the past N days (for a given N). It was developed by a publisher and promoter of trading materials, Larry Williams.
        Its purpose is to tell whether a stock or commodity market is trading near the high or the low, or somewhere in between,
        of its recent trading range.
        The oscillator is on a negative scale, from −100 (lowest) up to 0 (highest).
    """

    highest_high = dataframe["high"].rolling(center=False, window=period).max()
    lowest_low = dataframe["low"].rolling(center=False, window=period).min()

    WR = Series(
        (highest_high - dataframe["close"]) / (highest_high - lowest_low),
        name="{0} Williams %R".format(period),
        )

    return WR * -100



# VWAP bands
def VWAPB(dataframe, window_size=20, num_of_std=1):
    df = dataframe.copy()
    df['vwap'] = qtpylib.rolling_vwap(df,window=window_size)
    rolling_std = df['vwap'].rolling(window=window_size).std()
    df['vwap_low'] = df['vwap'] - (rolling_std * num_of_std)
    df['vwap_high'] = df['vwap'] + (rolling_std * num_of_std)
    return df['vwap_low'], df['vwap'], df['vwap_high']

def bollinger_bands(stock_price, window_size, num_of_std):
    rolling_mean = stock_price.rolling(window=window_size).mean()
    rolling_std = stock_price.rolling(window=window_size).std()
    lower_band = rolling_mean - (rolling_std * num_of_std)
    return np.nan_to_num(rolling_mean), np.nan_to_num(lower_band)

#Chaikin Money Flow
def chaikin_money_flow(dataframe, n=20, fillna=False) -> Series:
    """Chaikin Money Flow (CMF)
    It measures the amount of Money Flow Volume over a specific period.
    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:chaikin_money_flow_cmf
    Args:
        dataframe(pandas.Dataframe): dataframe containing ohlcv
        n(int): n period.
        fillna(bool): if True, fill nan values.
    Returns:
        pandas.Series: New feature generated.
    """
    mfv = ((dataframe['close'] - dataframe['low']) - (dataframe['high'] - dataframe['close'])) / (dataframe['high'] - dataframe['low'])
    mfv = mfv.fillna(0.0)  # float division by zero
    mfv *= dataframe['volume']
    cmf = (mfv.rolling(n, min_periods=0).sum()
           / dataframe['volume'].rolling(n, min_periods=0).sum())
    if fillna:
        cmf = cmf.replace([np.inf, -np.inf], np.nan).fillna(0)
    return Series(cmf, name='cmf')


def ha_typical_price(bars):
    res = (bars['ha_high'] + bars['ha_low'] + bars['ha_close']) / 3.
    return Series(index=bars.index, data=res)


class GeneStrategy(IStrategy):
    def version(self) -> str:
        return "2024-12-23 03:29:01"

    """
    PASTE OUTPUT FROM HYPEROPT HERE
    Can be overridden for specific sub-strategies (stake currencies) at the bottom.
    """
    
    # ROI table:
    minimal_roi = {
        "0": 100
    }
    #dca
    position_adjustment_enable = True

    # Stoploss:
    stoploss = -0.99  # use custom stoploss

    # Trailing stop:
    trailing_stop = False
    trailing_stop_positive = 0.02 #povodne 0.001
    trailing_stop_positive_offset = 0.10 #povodne 0.012
    trailing_only_offset_is_reached = True
    #dca
    position_adjustment_enable = True

    timeframe = '5m'

    # Make sure these match or are not overridden in config
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    
    
    # Custom stoploss
    use_custom_stoploss = False

    process_only_new_candles = True
    startup_candle_count = 168

    order_types = {
        'entry': 'market',
        'exit': 'market',
        'emergencyexit': 'market',
        'forceentry': "market",
        'forceexit': 'market',
        'stoploss': 'market',
        'stoploss_on_exchange': False,

        'stoploss_on_exchange_interval': 60,
        'stoploss_on_exchange_limit_ratio': 0.99
    }
    
    def is_support(self, row_data) -> bool:
        conditions = []
        for row in range(len(row_data)-1):
            if row < len(row_data)/2:
                conditions.append(row_data[row] > row_data[row+1])
            else:
                conditions.append(row_data[row] < row_data[row+1])
        return reduce(lambda x, y: x & y, conditions)
    
    # Protection (NFIX29)
    fast_ewo = 50
    slow_ewo = 200
    
    
    #NFINext44
    
    buy_44_ma_offset = 0.982
    buy_44_ewo = -18.143
    buy_44_cti = -0.8
    buy_44_r_1h = -75.0

    #NFINext37
    buy_37_ma_offset = 0.98
    buy_37_ewo = 9.8
    buy_37_rsi = 56.0
    buy_37_cti = -0.7

    #NFINext7
    buy_ema_open_mult_7 = 0.030
    buy_cti_7 = -0.89
    
    buy_rmi = IntParameter(30.0, 50.0, default=45, space='buy', optimize=True)
    buy_cci = IntParameter(-135.0, -90.0, default=-126, space='buy', optimize=True)
    buy_srsi_fk = IntParameter(30.0, 50.0, default=42, space='buy', optimize=True)
    buy_cci_length = IntParameter(25.0, 45.0, default=42, space='buy', optimize=True)
    buy_rmi_length = IntParameter(8.0, 20.0, default=11, space='buy', optimize=True)

    buy_bb_width = DecimalParameter(0.065, 0.135, default=0.097, space='buy', optimize=True)
    buy_bb_delta = DecimalParameter(0.018, 0.035, default=0.028, space='buy', optimize=True)
    
    buy_roc_1h = IntParameter(-25.0, 200.0, default=13, space='buy', optimize=True)
    buy_bb_width_1h = DecimalParameter(0.3, 2.0, default=1.3, space='buy', optimize=True)

    #ClucHA
    is_optimize_clucha = False
    buy_clucha_bbdelta_close = DecimalParameter(0.0005, 0.02, default=0.001, space='buy', optimize=True)
    buy_clucha_bbdelta_tail = DecimalParameter(0.7, 1.0, default=1.0, space='buy', optimize=True)
    buy_clucha_close_bblower = DecimalParameter(0.0005, 0.02, default=0.008, space='buy', optimize=True)
    buy_clucha_closedelta_close = DecimalParameter(0.0005, 0.02, default=0.014, space='buy', optimize=True)
    buy_clucha_rocr_1h = DecimalParameter(0.5, 1.0, default=0.51, space='buy', optimize=True)
    
    #Local_Uptrend    
    buy_ema_diff = DecimalParameter(0.022, 0.027, default=0.026, space='buy', optimize=True)
    buy_bb_factor = DecimalParameter(0.99, 0.999, default=0.995, space='buy', optimize=True)
    buy_closedelta = DecimalParameter(12.0, 18.0, default=13.1, space='buy', optimize=True)
    
    # buy params
    rocr_1h = DecimalParameter(0.5, 1.0, default=0.51, space='buy', optimize=True)
    rocr1_1h = DecimalParameter(0.5, 1.0, default=0.59, space='buy', optimize=True)
    bbdelta_close = DecimalParameter(0.0005, 0.02, default=0.001, space='buy', optimize=True)
    closedelta_close = DecimalParameter(0.0005, 0.02, default=0.014, space='buy', optimize=True)
    bbdelta_tail = DecimalParameter(0.7, 1.0, default=1.0, space='buy', optimize=True)
    close_bblower = DecimalParameter(0.0005, 0.02, default=0.008, space='buy', optimize=True)

    # sell params
    sell_fisher = DecimalParameter(0.1, 0.5, default=0.5, space='sell', optimize=True)
    sell_bbmiddle_close = DecimalParameter(0.97, 1.1, default=1.067, space='sell', optimize=True)
    
    #Deadfish
    sell_deadfish_bb_width = DecimalParameter(0.03, 0.75, default=0.06, space='sell', optimize=True)
    sell_deadfish_profit = DecimalParameter(-0.15, -0.05, default=-0.1, space='sell', optimize=True)
    sell_deadfish_bb_factor = DecimalParameter(0.9, 1.2, default=1.2, space='sell', optimize=True)
    sell_deadfish_volume_factor = DecimalParameter(1.0, 2.5, default=1.9, space='sell', optimize=True)
    
    # SMAOffset
    base_nb_candles_buy = IntParameter(8.0, 20.0, default=13, space='buy', optimize=True)
    base_nb_candles_sell = IntParameter(8.0, 50.0, default=44, space='sell', optimize=True)
    low_offset = DecimalParameter(0.985, 0.995, default=0.991, space='buy', optimize=True)
    high_offset = DecimalParameter(1.005, 1.015, default=1.007, space='sell', optimize=True)
    high_offset_2 = DecimalParameter(1.01, 1.02, default=1.01, space='sell', optimize=True)
    
    sell_trail_profit_min_1 = DecimalParameter(0.1, 0.25, default=0.25, space='sell', optimize=True)
    sell_trail_profit_max_1 = DecimalParameter(0.3, 0.5, default=0.5, space='sell', optimize=True)
    sell_trail_down_1 = DecimalParameter(0.04, 0.1, default=0.08, space='sell', optimize=True)

    sell_trail_profit_min_2 = DecimalParameter(0.04, 0.1, default=0.04, space='sell', optimize=True)
    sell_trail_profit_max_2 = DecimalParameter(0.08, 0.25, default=0.08, space='sell', optimize=True)
    sell_trail_down_2 = DecimalParameter(0.04, 0.2, default=0.07, space='sell', optimize=True)

    # hard stoploss profit
    pHSL = DecimalParameter(-0.5, -0.04, default=-0.163, space='sell', optimize=True)
    # profit threshold 1, trigger point, SL_1 is used
    pPF_1 = DecimalParameter(0.008, 0.02, default=0.01, space='sell', optimize=True)
    pSL_1 = DecimalParameter(0.008, 0.02, default=0.008, space='sell', optimize=True)

    # profit threshold 2, SL_2 is used
    pPF_2 = DecimalParameter(0.04, 0.1, default=0.072, space='sell', optimize=True)
    pSL_2 = DecimalParameter(0.02, 0.07, default=0.054, space='sell', optimize=True)
    
    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, '1h') for pair in pairs]

        informative_pairs += [("BTC/USDT", "5m"),
                             ]
        return informative_pairs
    
    def custom_sell(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float, current_profit: float, **kwargs):
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
        filled_buys = trade.select_filled_orders('buy')
        count_of_buys = len(filled_buys)

        #previous_candle_1 = dataframe.iloc[-1].squeeze()
        #previous_candle_2 = dataframe.iloc[-2].squeeze()
        #previous_candle_3 = dataframe.iloc[-3].squeeze()
        #max_profit = ((trade.max_rate - trade.open_rate) / trade.open_rate)
        #max_loss = ((trade.open_rate - trade.min_rate) / trade.min_rate)

        #if current_profit < -0.04 and (current_time - trade.open_date_utc).days >= 4:
        #    return 'unclog'

        if (last_candle is not None):
            #if (current_time - timedelta(minutes=30) > trade.open_date_utc) & (trade.open_date_utc + timedelta(minutes=15000) > current_time) & (last_candle['close'] < last_candle['ema_200']):
             #    return 'dlho_to_trva'


        
            #if (current_time - timedelta(minutes=120) > trade.open_date_utc) & (current_profit > self.sell_custom_roi_profit_4.value) & (last_candle['rsi'] < self.sell_custom_roi_rsi_4.value):
            #    return 'roi_target_4'
            #elif (current_time - timedelta(minutes=120) > trade.open_date_utc) & (current_profit > self.sell_custom_roi_profit_3.value) & (last_candle['rsi'] < self.sell_custom_roi_rsi_3.value):
            #    return 'roi_target_3'
            #elif (current_time - timedelta(minutes=120) > trade.open_date_utc) & (current_profit > self.sell_custom_roi_profit_2.value) & (last_candle['rsi'] < self.sell_custom_roi_rsi_2.value):
            #    return 'roi_target_2'
            #elif (current_time - timedelta(minutes=300) > trade.open_date_utc) & (current_profit > self.sell_custom_roi_profit_1.value) & (last_candle['rsi'] < self.sell_custom_roi_rsi_1.value):
            #    return 'roi_target_1'
            #elif (current_time - timedelta(minutes=400) > trade.open_date_utc) & (current_profit > 0) & (current_profit < self.sell_custom_roi_profit_5.value) & (last_candle['sma_200_dec_1h']):
            #    return 'roi_target_5'

            if (current_profit > self.sell_trail_profit_min_1.value) & (current_profit < self.sell_trail_profit_max_1.value) & (((trade.max_rate - trade.open_rate) / 100) > (current_profit + self.sell_trail_down_1.value)):
                return 'trail_target_1'
            elif (current_profit > self.sell_trail_profit_min_2.value) & (current_profit < self.sell_trail_profit_max_2.value) & (((trade.max_rate - trade.open_rate) / 100) > (current_profit + self.sell_trail_down_2.value)):
                return 'trail_target_2'
            elif (current_profit > 3) & (last_candle['rsi'] > 85):
                 return 'RSI-85 target'

            #if (current_profit > 3) & (last_candle['close'] > last_candle['bb_upperband'])  & (previous_candle_1['close'] > previous_candle_1['bb_upperband']) & (previous_candle_2['close'] > previous_candle_2['bb_upperband']) & (previous_candle_3['close'] > previous_candle_3['bb_upperband']) & (last_candle['volume'] > 0):
            #    return 'BB_Upper Sell signal'


        


   
            
            if (current_profit > 0) & (count_of_buys < 4) & (last_candle['close'] > last_candle['hma_50']) & (last_candle['close'] > (last_candle[f'ma_sell_{self.base_nb_candles_sell.value}'] * self.high_offset_2.value)) & (last_candle['rsi']>50) & (last_candle['volume'] > 0) & (last_candle['rsi_fast'] > last_candle['rsi_slow']):
                return 'sell signal1'
            if (current_profit > 0) & (count_of_buys >= 4) & (last_candle['close'] > last_candle['hma_50'] * 1.01) & (last_candle['close'] > (last_candle[f'ma_sell_{self.base_nb_candles_sell.value}'] * self.high_offset_2.value)) & (last_candle['rsi']>50) & (last_candle['volume'] > 0) & (last_candle['rsi_fast'] > last_candle['rsi_slow']):
                return 'sell signal1 * 1.01'
            if (current_profit > 0) & (last_candle['close'] > last_candle['hma_50']) & (last_candle['close'] > (last_candle[f'ma_sell_{self.base_nb_candles_sell.value}'] * self.high_offset.value)) &  (last_candle['volume'] > 0) & (last_candle['rsi_fast'] > last_candle['rsi_slow']):
                return 'sell signal2'
            #if (current_profit < -0.15) & (last_candle['rsi_1d'] < 20) & (last_candle['cmf'] < -0.0) & (last_candle['sma_200_dec_20']) & (last_candle['sma_200_dec_24']) & (current_time - timedelta(minutes=9200) > trade.open_date_utc):
                return 'sell stoploss1'
            #if (current_profit < -0.25) & (last_ca
            


            
            
            if (    (current_profit < self.sell_deadfish_profit.value)
                and (last_candle['close'] < last_candle['ema_200'])
                and (last_candle['bb_width'] < self.sell_deadfish_bb_width.value)
                and (last_candle['close'] > last_candle['bb_middleband2'] * self.sell_deadfish_bb_factor.value)
                and (last_candle['volume_mean_12'] < last_candle['volume_mean_24'] * self.sell_deadfish_volume_factor.value)
                and (last_candle['cmf'] < 0.0)
            ):
                return f"sell_stoploss_deadfish"
            
            


    # come from BB_RPB_TSL
    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:

        # hard stoploss profit
        HSL = self.pHSL.value
        PF_1 = self.pPF_1.value
        SL_1 = self.pSL_1.value
        PF_2 = self.pPF_2.value
        SL_2 = self.pSL_2.value

        # For profits between PF_1 and PF_2 the stoploss (sl_profit) used is linearly interpolated
        # between the values of SL_1 and SL_2. For all profits above PL_2 the sl_profit value
        # rises linearly with current profit, for profits below PF_1 the hard stoploss profit is used.

        if current_profit > PF_2:
            sl_profit = SL_2 + (current_profit - PF_2)
        elif current_profit > PF_1:
            sl_profit = SL_1 + ((current_profit - PF_1) * (SL_2 - SL_1) / (PF_2 - PF_1))
        else:
            sl_profit = HSL

        # Only for hyperopt invalid return
        if sl_profit >= current_profit:
            return -0.99

        return stoploss_from_open(sl_profit, current_profit)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        
        
        info_tf = '5m'

        informative = self.dp.get_pair_dataframe('BTC/USDT', timeframe=info_tf)
        informative_btc = informative.copy().shift(1)
        #informative = self.dp.get_pair_dataframe('BTC/USDT', timeframe=inf_tf)
        #informative_btc = informative.copy().shift(1)

        dataframe['btc_close'] = informative_btc['close']
        dataframe['btc_ema_fast'] = ta.EMA(informative_btc, timeperiod=20)
        dataframe['btc_ema_slow'] = ta.EMA(informative_btc, timeperiod=25)
        dataframe['down'] = (dataframe['btc_ema_fast'] < dataframe['btc_ema_slow']).astype('int')
        
        # Calculate all ma_sell values
        for val in self.base_nb_candles_sell.range:
             dataframe[f'ma_sell_{val}'] = ta.EMA(dataframe, timeperiod=val)
        
        dataframe['volume_mean_12'] = dataframe['volume'].rolling(12).mean().shift(1)
        dataframe['volume_mean_24'] = dataframe['volume'].rolling(24).mean().shift(1)
        
        dataframe['cmf'] = chaikin_money_flow(dataframe, 20)
        
        # Bollinger bands
        bollinger2 = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband2'] = bollinger2['lower']
        dataframe['bb_middleband2'] = bollinger2['mid']
        dataframe['bb_upperband2'] = bollinger2['upper']
        dataframe['bb_width'] = ((dataframe['bb_upperband2'] - dataframe['bb_lowerband2']) / dataframe['bb_middleband2'])
        
        ## BB 40
        bollinger2_40 = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=40, stds=2)
        dataframe['bb_lowerband2_40'] = bollinger2_40['lower']
        dataframe['bb_middleband2_40'] = bollinger2_40['mid']
        dataframe['bb_upperband2_40'] = bollinger2_40['upper']
        
        
        
        #EMA
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_fast'] = ta.RSI(dataframe, timeperiod=4)
        dataframe['rsi_slow'] = ta.RSI(dataframe, timeperiod=20)
        dataframe['rsi_84'] = ta.RSI(dataframe, timeperiod=84)
        dataframe['rsi_112'] = ta.RSI(dataframe, timeperiod=112)
        
        # # Heikin Ashi Candles
        heikinashi = qtpylib.heikinashi(dataframe)
        dataframe['ha_open'] = heikinashi['open']
        dataframe['ha_close'] = heikinashi['close']
        dataframe['ha_high'] = heikinashi['high']
        dataframe['ha_low'] = heikinashi['low']
        
        # ClucHA
        dataframe['bb_delta_cluc'] = (dataframe['bb_middleband2_40'] - dataframe['bb_lowerband2_40']).abs()
        dataframe['ha_closedelta'] = (dataframe['ha_close'] - dataframe['ha_close'].shift()).abs()
        
        # SRSI hyperopt (is DIP)
        stoch = ta.STOCHRSI(dataframe, 15, 20, 2, 2)
        dataframe['srsi_fk'] = stoch['fastk']
        dataframe['srsi_fd'] = stoch['fastd']

        # Set Up Bollinger Bands
        mid, lower = bollinger_bands(ha_typical_price(dataframe), window_size=40, num_of_std=2)
        dataframe['lower'] = lower
        dataframe['mid'] = mid

        dataframe['bbdelta'] = (mid - dataframe['lower']).abs()
        dataframe['closedelta'] = (dataframe['ha_close'] - dataframe['ha_close'].shift()).abs()
        dataframe['tail'] = (dataframe['ha_close'] - dataframe['ha_low']).abs()

        dataframe['bb_lowerband'] = dataframe['lower']
        dataframe['bb_middleband'] = dataframe['mid']
        
        # is DIP
        bollinger3 = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=3)
        dataframe['bb_lowerband3'] = bollinger3['lower']
        dataframe['bb_middleband3'] = bollinger3['mid']
        dataframe['bb_upperband3'] = bollinger3['upper']
        dataframe['bb_delta'] = ((dataframe['bb_lowerband2'] - dataframe['bb_lowerband3']) / dataframe['bb_lowerband2'])

        dataframe['ema_fast'] = ta.EMA(dataframe['ha_close'], timeperiod=3)
        dataframe['ema_slow'] = ta.EMA(dataframe['ha_close'], timeperiod=50)
        dataframe['volume_mean_slow'] = dataframe['volume'].rolling(window=30).mean()
        dataframe['rocr'] = ta.ROCR(dataframe['ha_close'], timeperiod=28)
        
         # VWAP
        vwap_low, vwap, vwap_high = VWAPB(dataframe, 20, 1)
        
        vwap_low, vwap, vwap_high = VWAPB(dataframe, 20, 1)
        dataframe['vwap_low'] = vwap_low
        
        dataframe['vwap_upperband'] = vwap_high
        dataframe['vwap_middleband'] = vwap
        dataframe['vwap_lowerband'] = vwap_low
        dataframe['vwap_width'] = ( (dataframe['vwap_upperband'] - dataframe['vwap_lowerband']) / dataframe['vwap_middleband'] ) * 100
        # Diff
        dataframe['ema_vwap_diff_50'] = ( ( dataframe['ema_50'] - dataframe['vwap_lowerband'] ) / dataframe['ema_50'] )
        
        # Dip protection
        dataframe['tpct_change_0']   = top_percent_change_dca(dataframe,0)
        dataframe['tpct_change_1']   = top_percent_change_dca(dataframe,1)
        dataframe['tcp_percent_4'] =   top_percent_change_dca(dataframe , 4)

        #NFINEXT44
        dataframe['ewo'] = ewo(dataframe, 50, 200)

        # SMA
        dataframe['sma_15'] = ta.SMA(dataframe, timeperiod=15)
        dataframe['sma_30'] = ta.SMA(dataframe, timeperiod=30)
        
        
        # RMI hyperopt
        for val in self.buy_rmi_length.range:
            dataframe[f'rmi_length_{val}'] = RMI(dataframe, length=val, mom=4)
            
        # CCI hyperopt
        for val in self.buy_cci_length.range:
            dataframe[f'cci_length_{val}'] = ta.CCI(dataframe, val)
        
        #CTI
        dataframe['cti'] = pta.cti(dataframe["close"], length=20)
        
        
        #NFIX39
        dataframe['bb_delta_cluc'] = (dataframe['bb_middleband2_40'] - dataframe['bb_lowerband2_40']).abs()
        
        #NFIX29
        dataframe['ema_16'] = ta.EMA(dataframe, timeperiod=16)

            
        
        dataframe['EWO'] = EWO(dataframe, self.fast_ewo, self.slow_ewo)
        
        #local_uptrend
        dataframe['ema_26'] = ta.EMA(dataframe, timeperiod=26)
        dataframe['ema_12'] = ta.EMA(dataframe, timeperiod=12)
        
        #insta_signal
        dataframe['r_14'] = williams_r(dataframe, period=14)
        
        #rebuy check if EMA is rising
        dataframe['ema_5'] = ta.EMA(dataframe, timeperiod=5)
        dataframe['ema_10'] = ta.EMA(dataframe, timeperiod=10)

        # Profit Maximizer - PMAX (NFINext37)
        dataframe['pm'], dataframe['pmx'] = pmax(heikinashi, MAtype=1, length=9, multiplier=27, period=10, src=3)
        dataframe['source'] = (dataframe['high'] + dataframe['low'] + dataframe['open'] + dataframe['close'])/4
        dataframe['pmax_thresh'] = ta.EMA(dataframe['source'], timeperiod=9)
        dataframe['sma_75'] = ta.SMA(dataframe, timeperiod=75)

        rsi = ta.RSI(dataframe)
        dataframe["rsi"] = rsi
        rsi = 0.1 * (rsi - 50)
        dataframe["fisher"] = (np.exp(2 * rsi) - 1) / (np.exp(2 * rsi) + 1)

        inf_tf = '1h'

        informative = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=inf_tf)

        inf_heikinashi = qtpylib.heikinashi(informative)

        informative['ha_close'] = inf_heikinashi['close']
        informative['rocr'] = ta.ROCR(informative['ha_close'], timeperiod=168)
        informative['rsi_14'] = ta.RSI(dataframe, timeperiod=14)
        informative['cmf'] = chaikin_money_flow(dataframe, 20)
        sup_series = informative['low'].rolling(window = 5, center=True).apply(lambda row: self.is_support(row), raw=True).shift(2)
        informative['sup_level'] = Series(np.where(sup_series, np.where(informative['close'] < informative['open'], informative['close'], informative['open']), float('NaN'))).ffill()
        informative['roc'] = ta.ROC(informative, timeperiod=9)

        informative['r_480'] = williams_r(informative, period=480)
        
        # Bollinger bands (is DIP)
        bollinger2 = qtpylib.bollinger_bands(qtpylib.typical_price(informative), window=20, stds=2)
        informative['bb_lowerband2'] = bollinger2['lower']
        informative['bb_middleband2'] = bollinger2['mid']
        informative['bb_upperband2'] = bollinger2['upper']
        informative['bb_width'] = ((informative['bb_upperband2'] - informative['bb_lowerband2']) / informative['bb_middleband2'])
        
        informative['r_84'] = williams_r(informative, period=84)
        informative['cti_40'] = pta.cti(informative["close"], length=40)
        
        
        dataframe['hma_50'] = qtpylib.hull_moving_average(dataframe['close'], window=50)
        

        dataframe = merge_informative_pair(dataframe, informative, self.timeframe, inf_tf, ffill=True)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        
        btc_dump = (
                (dataframe['btc_close'].rolling(24).max() >= (dataframe['btc_close'] * 1.03 ))
            )  
        rsi_check = (
                (dataframe['rsi_84'] < 60) &
                (dataframe['rsi_112'] < 60)
            ) 

        dataframe.loc[
                ((dataframe[f'rmi_length_{self.buy_rmi_length.value}'] < self.buy_rmi.value) &
                (dataframe[f'cci_length_{self.buy_cci_length.value}'] <= self.buy_cci.value) &
                (dataframe['srsi_fk'] < self.buy_srsi_fk.value) &
                (dataframe['bb_delta'] > self.buy_bb_delta.value) &
                (dataframe['bb_width'] > self.buy_bb_width.value) &
                (dataframe['closedelta'] > dataframe['close'] * self.buy_closedelta.value / 1000 ) &    # from BinH
                (dataframe['close'] < dataframe['bb_lowerband3'] * self.buy_bb_factor.value)&
                (dataframe['roc_1h'] < self.buy_roc_1h.value) &
                (dataframe['bb_width_1h'] < self.buy_bb_width_1h.value)
            ),
        ['enter_long', 'enter_tag']] = (1, 'DIP signal')     

        dataframe.loc[

                ((dataframe['bb_delta'] > self.buy_bb_delta.value) &
                (dataframe['bb_width'] > self.buy_bb_width.value) &
                (dataframe['closedelta'] > dataframe['close'] * self.buy_closedelta.value / 1000 ) &    # from BinH
                (dataframe['close'] < dataframe['bb_lowerband3'] * self.buy_bb_factor.value)&
                (dataframe['roc_1h'] < self.buy_roc_1h.value) &
                (dataframe['bb_width_1h'] < self.buy_bb_width_1h.value)

            ),
        ['enter_long', 'enter_tag']] = (1, 'Break signal')    
        
        
        
        
        
        
        dataframe.loc[
                        
                    ((dataframe['rocr_1h'] > self.buy_clucha_rocr_1h.value ) &
                
                        (dataframe['bb_lowerband2_40'].shift() > 0) &
                        (dataframe['bb_delta_cluc'] > dataframe['ha_close'] * self.buy_clucha_bbdelta_close.value) &
                        (dataframe['ha_closedelta'] > dataframe['ha_close'] * self.buy_clucha_closedelta_close.value) &
                        (dataframe['tail'] < dataframe['bb_delta_cluc'] * self.buy_clucha_bbdelta_tail.value) &
                        (dataframe['ha_close'] < dataframe['bb_lowerband2_40'].shift()) &
                        (dataframe['close'] > (dataframe['sup_level_1h'] * 0.88)) &
                        (dataframe['ha_close'] < dataframe['ha_close'].shift()) 
            
                    ),
        ['enter_long', 'enter_tag']] = (1, 'cluc_HA')    
        
         
        dataframe.loc[    
                ((dataframe['ema_200'] > (dataframe['ema_200'].shift(12) * 1.01)) &
                (dataframe['ema_200'] > (dataframe['ema_200'].shift(48) * 1.07)) &
                (dataframe['bb_lowerband2_40'].shift().gt(0)) &
                (dataframe['bb_delta_cluc'].gt(dataframe['close'] * 0.056)) &
                (dataframe['closedelta'].gt(dataframe['close'] * 0.01)) &
                (dataframe['tail'].lt(dataframe['bb_delta_cluc'] * 0.5)) &
                (dataframe['close'].lt(dataframe['bb_lowerband2_40'].shift())) &
                (dataframe['close'].le(dataframe['close'].shift())) &
                (dataframe['close'] > dataframe['ema_50'] * 0.912)
            
            ),
        ['enter_long', 'enter_tag']] = (1, 'NFIX39')
        
        dataframe.loc[
                ((dataframe['close'] > (dataframe['sup_level_1h'] * 0.72)) &
                (dataframe['close'] < (dataframe['ema_16'] * 0.982)) &
                (dataframe['EWO'] < -10.0) &
                (dataframe['cti'] < -0.9)

            ),
        ['enter_long', 'enter_tag']] = (1, 'NFIX29')
        
        dataframe.loc[
                ((dataframe['ema_26'] > dataframe['ema_12']) &
                (dataframe['ema_26'] - dataframe['ema_12'] > dataframe['open'] * self.buy_ema_diff.value) &
                (dataframe['ema_26'].shift() - dataframe['ema_12'].shift() > dataframe['open'] / 100) &
                (dataframe['close'] < dataframe['bb_lowerband2'] * self.buy_bb_factor.value) &
                (dataframe['closedelta'] > dataframe['close'] * self.buy_closedelta.value / 1000 ) 
                
             ),
        ['enter_long', 'enter_tag']] = (1, 'local_uptrend')
        
        dataframe.loc[
                (
                
                (dataframe['close'] < dataframe['vwap_low']) &
                (dataframe['tcp_percent_4'] > 0.053) & # 0.053)
                (dataframe['cti'] < -0.8) & # -0.8)
                (dataframe['rsi'] < 35) &
                (dataframe['rsi_84'] < 60) &
                (dataframe['rsi_112'] < 60) &
                #(dataframe['cmf'] > -0.20) & # povodne som mal -0.10
                (dataframe['volume'] > 0)
           ),
        ['enter_long', 'enter_tag']] = (1, 'vwap')
        
        dataframe.loc[
                ((dataframe['bb_width_1h'] > 0.131) &
                (dataframe['r_14'] < -51) &
                (dataframe['r_84_1h'] < -70) &
                (dataframe['cti'] < -0.845) &
                (dataframe['cti_40_1h'] < -0.735)
                &
                ( (dataframe['close'].rolling(48).max() >= (dataframe['close'] * 1.1 )) ) &
                #(btc_dump == 0) &
                #(dataframe['tcp_percent_4'] > 0.053) & # 0.053) 
                (dataframe['btc_close'].rolling(24).max() >= (dataframe['btc_close'] * 1.03 ))
          ),
        ['enter_long', 'enter_tag']] = (1, 'insta_signal') 

        dataframe.loc[
            ((dataframe['close'] < (dataframe['ema_16'] * self.buy_44_ma_offset))&
            (dataframe['ewo'] < self.buy_44_ewo)&
            (dataframe['cti'] < self.buy_44_cti)&
            (dataframe['r_480_1h'] < self.buy_44_r_1h)&
            #(dataframe['tcp_percent_4'] > 0.053) & # 0.053)
            (dataframe['volume'] > 0)
          ),
        ['enter_long', 'enter_tag']] = (1, 'NFINext44') 


        dataframe.loc[  
            ((dataframe['pm'] > dataframe['pmax_thresh'])&
            (dataframe['close'] < dataframe['sma_75'] * self.buy_37_ma_offset)&
            (dataframe['ewo'] > self.buy_37_ewo)&
            (dataframe['rsi'] < self.buy_37_rsi)&
            (dataframe['cti'] < self.buy_37_cti)
            #(dataframe['safe_dump_50_1h'])  
        ),
        ['enter_long', 'enter_tag']] = (1, 'NFINext37')   

        dataframe.loc[ 
            ((dataframe['ema_26'] > dataframe['ema_12'])&
            ((dataframe['ema_26'] - dataframe['ema_12']) > (dataframe['open'] * self.buy_ema_open_mult_7))&
            ((dataframe['ema_26'].shift() - dataframe['ema_12'].shift()) > (dataframe['open'] / 100))&
            (dataframe['cti'] < self.buy_cti_7)      

        ),        
        ['enter_long', 'enter_tag']] = (1, 'NFINext7')   

#newstrat52
        dataframe.loc[
                ((dataframe['rsi_slow'] < dataframe['rsi_slow'].shift(1)) &
                (dataframe['rsi_fast'] < 46) &
                (dataframe['rsi'] > 19) &
                (dataframe['close'] < dataframe['sma_15'] * 0.942) &
                (dataframe['cti'] < -0.86)
        ),        
        ['enter_long', 'enter_tag']] = (1, 'NFINext32')



        dataframe.loc[
                ((dataframe['bb_lowerband2_40'].shift() > 0) &
                (dataframe['bb_delta_cluc'] > dataframe['close'] * 0.059) &
                (dataframe['ha_closedelta'] > dataframe['close'] * 0.023) &
                (dataframe['tail'] < dataframe['bb_delta_cluc'] * 0.24) &
                (dataframe['close'] < dataframe['bb_lowerband2_40'].shift()) &
                (dataframe['close'] < dataframe['close'].shift()) &
                (btc_dump == 0)
        ),        
        ['enter_long', 'enter_tag']] = (1, 'sma_3')

        dataframe.loc[
                ((dataframe['close'] < dataframe['vwap_lowerband']) &
                (dataframe['tpct_change_1'] > 0.04) &
                (dataframe['cti'] < -0.8) &
                (dataframe['rsi'] < 35) &
                (rsi_check) &
                (btc_dump == 0)
        ),        
        ['enter_long', 'enter_tag']] = (1, 'WVAP')

      
        return dataframe



    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        dataframe.loc[
            (dataframe['fisher'] > self.sell_fisher.value) &
            (dataframe['ha_high'].le(dataframe['ha_high'].shift(1))) &
            (dataframe['ha_high'].shift(1).le(dataframe['ha_high'].shift(2))) &
            (dataframe['ha_close'].le(dataframe['ha_close'].shift(1))) &
            (dataframe['ema_fast'] > dataframe['ha_close']) &
            ((dataframe['ha_close'] * self.sell_bbmiddle_close.value) > dataframe['bb_middleband']) &
            (dataframe['volume'] > 0),
            'sell'
        ] = 0

        return dataframe
    

    
   
   
   
    initial_safety_order_trigger = -0.018
    max_safety_orders = 8
    safety_order_step_scale = 1.2
    safety_order_volume_scale = 1.4
    
    
    
    
    def top_percent_change_dca(self, dataframe: DataFrame, length: int) -> float:
        """
        Percentage change of the current close from the range maximum Open price

        :param dataframe: DataFrame The original OHLC dataframe
        :param length: int The length to look back
        """
        if length == 0:
            return (dataframe['open'] - dataframe['close']) / dataframe['close']
        else:
            return (dataframe['open'].rolling(length).max() - dataframe['close']) / dataframe['close']
        
    
 
  
       


    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float, min_stake: float,
                              max_stake: float, **kwargs):
        if current_profit > self.initial_safety_order_trigger:
            return None

        # credits to reinuvader for not blindly executing safety orders
        # Obtain pair dataframe.
        dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        # Only buy when it seems it's climbing back up
        last_candle = dataframe.iloc[-1].squeeze()
        #previous_candle = dataframe.iloc[-2].squeeze()
        #previous2_candle = dataframe.iloc[-3].squeeze()
        #if last_candle['close'] / previous_candle['close'] < 1.02 :
        #if last_candle['close'] < previous_candle['close']:

        filled_buys = trade.select_filled_orders('buy')
        count_of_buys = len(filled_buys)
        if count_of_buys == 1 and (last_candle['tpct_change_0'] > 0.018) and (last_candle['close'] < last_candle['open']) :
            
                return None
        elif count_of_buys == 2 and (last_candle['tpct_change_0'] > 0.018) and (last_candle['close'] < last_candle['open']) and (last_candle['ema_vwap_diff_50'] < 0.215):
            
                return None
        elif count_of_buys == 3 and (last_candle['tpct_change_0'] > 0.018) and (last_candle['close'] < last_candle['open'])and (last_candle['ema_vwap_diff_50'] < 0.215) :
           
                
                return None
        elif count_of_buys == 4 and (last_candle['tpct_change_0'] > 0.018) and (last_candle['close'] < last_candle['open'])and (last_candle['ema_vwap_diff_50'] < 0.215) and (last_candle['ema_5']) >= (last_candle['ema_10']):
            
                
                return None
        elif count_of_buys == 5 and (last_candle['cmf_1h'] < 0.00) and (last_candle['close'] < last_candle['open']) and (last_candle['rsi_14_1h'] < 30) and (last_candle['tpct_change_0'] > 0.018) and (last_candle['close'] < last_candle['open']) and (last_candle['ema_vwap_diff_50'] < 0.215) and (last_candle['ema_5']) >= (last_candle['ema_10']):
           
                logger.info(f"DCA for {trade.pair} waiting for cmf_1h ({last_candle['cmf_1h']}) to rise above 0. Waiting for rsi_1h ({last_candle['rsi_14_1h']})to rise above 30")
                return None
        elif count_of_buys == 6 and (last_candle['cmf_1h'] < 0.00) and (last_candle['close'] < last_candle['open']) and (last_candle['rsi_14_1h'] < 30) and (last_candle['tpct_change_0'] > 0.018) and (last_candle['close'] < last_candle['open'] and (last_candle['ema_vwap_diff_50'] < 0.215)) and (last_candle['ema_5']) >= (last_candle['ema_10']): 
            
                logger.info(f"DCA for {trade.pair} waiting for cmf_1h ({last_candle['cmf_1h']}) to rise above 0. Waiting for rsi_1h ({last_candle['rsi_14_1h']})to rise above 30")
                return None
        elif count_of_buys == 7 and (last_candle['cmf_1h'] < 0.00) and (last_candle['close'] < last_candle['open']) and (last_candle['rsi_14_1h'] < 30) and (last_candle['tpct_change_0'] > 0.018) and (last_candle['close'] < last_candle['open'] and (last_candle['ema_vwap_diff_50'] < 0.215)) and (last_candle['ema_5']) >= (last_candle['ema_10']):
            
                logger.info(f"DCA for {trade.pair} waiting for cmf_1h ({last_candle['cmf_1h']}) to rise above 0. Waiting for rsi_1h ({last_candle['rsi_14_1h']})to rise above 30")
                return None
        elif count_of_buys == 8 and (last_candle['cmf_1h'] < 0.00) and (last_candle['close'] < last_candle['open']) and (last_candle['rsi_14_1h'] < 30) and (last_candle['tpct_change_0'] > 0.018) and (last_candle['close'] < last_candle['open'] and (last_candle['ema_vwap_diff_50'] < 0.215)) and (last_candle['ema_5']) >= (last_candle['ema_10']):
            
                logger.info(f"DCA for {trade.pair} waiting for cmf_1h ({last_candle['cmf_1h']}) to rise above 0. Waiting for rsi_1h ({last_candle['rsi_14_1h']})to rise above 30")
                return None
        
        
        #if (last_candle['cmf_1h'] < 0.00) and (last_candle['close'] < last_candle['open']) and (last_candle['rsi_14_1h'] < 30):
         #   logger.info(f"DCA for {trade.pair} waiting for cmf_1h ({last_candle['cmf_1h']}) to rise above 0. Waiting for rsi_1h ({last_candle['rsi_14_1h']})to rise above 30")
        #if (last_candle['tpct_change_0'] > 0.018) and (last_candle['close'] < last_candle['open']):
         #   return None

        #count_of_buys = 0
        #for order in trade.orders:
        #    if order.ft_is_open or order.ft_order_side != 'buy':
        #        continue
        #    if order.status == "closed":
        #        count_of_buys += 1



        
        
        if 1 <= count_of_buys <= self.max_safety_orders:
            safety_order_trigger = (abs(self.initial_safety_order_trigger) * count_of_buys)
            if (self.safety_order_step_scale > 1):
                safety_order_trigger = abs(self.initial_safety_order_trigger) + (abs(self.initial_safety_order_trigger) * self.safety_order_step_scale * (math.pow(self.safety_order_step_scale,(count_of_buys - 1)) - 1) / (self.safety_order_step_scale - 1))
            elif (self.safety_order_step_scale < 1):
                safety_order_trigger = abs(self.initial_safety_order_trigger) + (abs(self.initial_safety_order_trigger) * self.safety_order_step_scale * (1 - math.pow(self.safety_order_step_scale,(count_of_buys - 1))) / (1 - self.safety_order_step_scale))

            if current_profit <= (-1 * abs(safety_order_trigger)):
                try:
                    # This returns first order stake size
                    stake_amount = filled_buys[0].cost
                    # This then calculates current safety order size
                    stake_amount = stake_amount * math.pow(self.safety_order_volume_scale,(count_of_buys - 1))
                    amount = stake_amount / current_rate
                    logger.info(f"Initiating safety order buy #{count_of_buys} for {trade.pair} with stake amount of {stake_amount} which equals {amount}")
                    return stake_amount
                except Exception as exception:
                    logger.info(f'Error occured while trying to get stake amount for {trade.pair}: {str(exception)}') 
                    return None

        return None

# PMAX
def pmax(df, period, multiplier, length, MAtype, src):

    period = int(period)
    multiplier = int(multiplier)
    length = int(length)
    MAtype = int(MAtype)
    src = int(src)

    mavalue = 'MA_' + str(MAtype) + '_' + str(length)
    atr = 'ATR_' + str(period)
    pm = 'pm_' + str(period) + '_' + str(multiplier) + '_' + str(length) + '_' + str(MAtype)
    pmx = 'pmX_' + str(period) + '_' + str(multiplier) + '_' + str(length) + '_' + str(MAtype)

    # MAtype==1 --> EMA
    # MAtype==2 --> DEMA
    # MAtype==3 --> T3
    # MAtype==4 --> SMA
    # MAtype==5 --> VIDYA
    # MAtype==6 --> TEMA
    # MAtype==7 --> WMA
    # MAtype==8 --> VWMA
    # MAtype==9 --> zema
    if src == 1:
        masrc = df["close"]
    elif src == 2:
        masrc = (df["high"] + df["low"]) / 2
    elif src == 3:
        masrc = (df["high"] + df["low"] + df["close"] + df["open"]) / 4

    if MAtype == 1:
        mavalue = ta.EMA(masrc, timeperiod=length)
    elif MAtype == 2:
        mavalue = ta.DEMA(masrc, timeperiod=length)
    elif MAtype == 3:
        mavalue = ta.T3(masrc, timeperiod=length)
    elif MAtype == 4:
        mavalue = ta.SMA(masrc, timeperiod=length)
    elif MAtype == 5:
        mavalue = VIDYA(df, length=length)
    elif MAtype == 6:
        mavalue = ta.TEMA(masrc, timeperiod=length)
    elif MAtype == 7:
        mavalue = ta.WMA(df, timeperiod=length)
    elif MAtype == 8:
        mavalue = vwma(df, length)
    elif MAtype == 9:
        mavalue = zema(df, period=length)

    df[atr] = ta.ATR(df, timeperiod=period)
    df['basic_ub'] = mavalue + ((multiplier/10) * df[atr])
    df['basic_lb'] = mavalue - ((multiplier/10) * df[atr])


    basic_ub = df['basic_ub'].values
    final_ub = np.full(len(df), 0.00)
    basic_lb = df['basic_lb'].values
    final_lb = np.full(len(df), 0.00)

    for i in range(period, len(df)):
        final_ub[i] = basic_ub[i] if (
            basic_ub[i] < final_ub[i - 1]
            or mavalue[i - 1] > final_ub[i - 1]) else final_ub[i - 1]
        final_lb[i] = basic_lb[i] if (
            basic_lb[i] > final_lb[i - 1]
            or mavalue[i - 1] < final_lb[i - 1]) else final_lb[i - 1]

    df['final_ub'] = final_ub
    df['final_lb'] = final_lb

    pm_arr = np.full(len(df), 0.00)
    for i in range(period, len(df)):
        pm_arr[i] = (
            final_ub[i] if (pm_arr[i - 1] == final_ub[i - 1]
                                    and mavalue[i] <= final_ub[i])
        else final_lb[i] if (
            pm_arr[i - 1] == final_ub[i - 1]
            and mavalue[i] > final_ub[i]) else final_lb[i]
        if (pm_arr[i - 1] == final_lb[i - 1]
            and mavalue[i] >= final_lb[i]) else final_ub[i]
        if (pm_arr[i - 1] == final_lb[i - 1]
            and mavalue[i] < final_lb[i]) else 0.00)

    pm = Series(pm_arr)

    # Mark the trend direction up/down
    pmx = np.where((pm_arr > 0.00), np.where((mavalue < pm_arr), 'down',  'up'), np.NaN)

    return pm, pmx
    
