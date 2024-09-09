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

    @staticmethod
    def constrain_gene(value, min_value, max_value):
        return max(min_value, min(value, max_value))

    def constrain_genes(self):
        self.genes[0] = self.constrain_gene(self.genes[0], 0.4, 0.99)  # initial_entry_ratio
        self.genes[1] = self.constrain_gene(self.genes[1], 0.3, 0.9)  # new_sl_coef
        self.genes[2] = self.constrain_gene(self.genes[2], 1, 30)  # lookback_length
        self.genes[3] = self.constrain_gene(self.genes[3], 1, 300)  # upper_trigger_level
        self.genes[4] = self.constrain_gene(self.genes[4], -300, -1)  # lower_trigger_level
        self.genes[5] = self.constrain_gene(self.genes[5], 25, 60)  # buy_rsi
        self.genes[6] = self.constrain_gene(self.genes[6], 50, 70)  # sell_rsi
        self.genes[7] = self.constrain_gene(self.genes[7], 1.0, 3.0)  # atr_multiplier
        self.genes[8] = self.constrain_gene(self.genes[8], 10, 50)  # swing_window
        self.genes[9] = self.constrain_gene(self.genes[9], 1, 10)  # swing_min_periods  
        self.genes[10] = self.constrain_gene(self.genes[10], 0.01, 0.1)  # swing_buffer
        self.genes[11] = self.constrain_gene(self.genes[11], -0.02, 0.02)  # buy_macd
        self.genes[12] = self.constrain_gene(self.genes[12], 5, 50)  # buy_ema_short
        self.genes[13] = self.constrain_gene(self.genes[13], 50, 200)  # buy_ema_long
        self.genes[14] = self.constrain_gene(self.genes[14], -0.02, 0.02)  # sell_macd
        self.genes[15] = self.constrain_gene(self.genes[15], 5, 50)  # sell_ema_short
        self.genes[16] = self.constrain_gene(self.genes[16], 50, 200)  # sell_ema_long
        self.genes[17] = self.constrain_gene(self.genes[17], 1, 30)  # volume_dca_int
        self.genes[18] = self.constrain_gene(self.genes[18], 1.0, 2.0)  # a_vol_coef
        self.genes[19] = self.constrain_gene(self.genes[19], 1, 100)  # dca_candles_modulo
        self.genes[20] = self.constrain_gene(self.genes[20], 0.01, 0.5)  # dca_threshold
        self.genes[21] = self.constrain_gene(self.genes[21], 1.0, 2.0)  # dca_multiplier
        self.genes[22] = self.constrain_gene(self.genes[22], 1, 5)  # max_dca_orders
        self.genes[23] = self.constrain_gene(self.genes[23], -0.20, -0.05)  # dca_profit_threshold

    # 在交叉和变异操作后调用此方法
    def after_genetic_operation(self):
        self.constrain_genes()


