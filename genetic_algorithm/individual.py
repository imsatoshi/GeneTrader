from typing import List
import random

class Individual:
    def __init__(self, genes: List[float]):
        self.genes = genes
        self.fitness = None

    @classmethod
    def create_random(cls):
        genes = [
            random.uniform(0.4, 0.99),      # initial_entry_ratio (Decimal)
            random.uniform(0.3, 0.9),      # new_sl_coef (Decimal)
            random.randint(1, 30),         # lookback_length (Int)
            random.randint(1, 300),        # upper_trigger_level (Int)
            random.randint(-300, -1),      # lower_trigger_level (Int)
            random.randint(25, 60),        # buy_rsi (Int)
            random.randint(50, 70),        # sell_rsi (Int)
            random.uniform(1.0, 3.0),      # atr_multiplier (Decimal)
            random.randint(10, 50),        # swing_window (Int)
            random.randint(1, 10),         # swing_min_periods (Int)
            random.uniform(0.01, 0.1),     # swing_buffer (Decimal)
            random.uniform(-0.02, 0.02),   # buy_macd (Decimal)
            random.randint(5, 50),         # buy_ema_short (Int)
            random.randint(50, 200),       # buy_ema_long (Int)
            random.uniform(-0.02, 0.02),   # sell_macd (Decimal)
            random.randint(5, 50),         # sell_ema_short (Int)
            random.randint(50, 200),       # sell_ema_long (Int)
            random.randint(1, 30),         # volume_dca_int (Int)
            random.uniform(1.0, 2.0),      # a_vol_coef (Decimal)
            random.randint(1, 100),        # dca_candles_modulo (Int)
            random.uniform(0.01, 0.5),     # dca_threshold (Decimal)
            random.uniform(1.0, 2.0),      # dca_multiplier (Decimal)
            random.randint(1, 5),          # max_dca_orders (Int)
            random.uniform(-0.20, -0.05),  # dca_profit_threshold (Decimal)
        ]
        return cls(genes)


