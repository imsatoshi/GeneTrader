from typing import List
import random

class Individual:
    def __init__(self, genes: List[float]):
        self.genes = genes
        self.fitness = None

    @classmethod
    def create_random(cls):
        genes = [
            random.uniform(0.4, 1.0),  # initial_entry_ratio
            random.uniform(0.3, 0.9),  # new_sl_coef
            random.randint(1, 30),     # lookback_length
            random.randint(1, 300),    # upper_trigger_level
            random.randint(-300, -1),  # lower_trigger_level
            random.randint(25, 60),    # buy_rsi
            random.randint(50, 70),    # sell_rsi
            random.uniform(1.0, 3.0),  # atr_multiplier
            random.randint(10, 50),    # swing_window
            random.randint(1, 10),     # swing_min_periods
            random.uniform(0.01, 0.1), # swing_buffer
            random.uniform(-0.02, 0.02), # buy_macd
            random.randint(5, 50),     # buy_ema_short
            random.randint(50, 200),   # buy_ema_long
            random.uniform(-0.02, 0.02), # sell_macd
            random.randint(5, 50),     # sell_ema_short
            random.randint(50, 200),   # sell_ema_long
            random.randint(1, 30),     # volume_dca_int
            random.uniform(1.0, 2.0),  # a_vol_coef
            random.randint(1, 100),    # dca_candles_modulo
            random.uniform(0.01, 0.5), # dca_threshold
            random.uniform(1.0, 2.0),  # dca_multiplier
            random.randint(1, 5),      # max_dca_orders
            random.uniform(-0.20, -0.05), # dca_profit_threshold
        ]
        return cls(genes)


