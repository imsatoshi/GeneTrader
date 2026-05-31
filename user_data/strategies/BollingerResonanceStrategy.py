"""Bollinger Resonance strategy template for future GA-driven evolution."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pandas as pd
from pandas import DataFrame

from freqtrade.strategy.interface import IStrategy

from bollinger_evolver.strategies.indicator_helpers import (
    DEFAULT_GENES,
    apply_entry_logic,
    apply_exit_logic,
    compute_bollinger_features,
    compute_resonance_scores,
    merge_informative_features,
)
from bollinger_evolver.strategies.position_sizing import (
    calculate_dca_stake,
    calculate_leverage,
    calculate_stake_amount,
    calculate_stoploss_from_atr,
    should_reduce_position,
)


class BollingerResonanceStrategy(IStrategy):
    """Multi-timeframe Bollinger resonance template for future evolution."""

    timeframe = "15m"
    can_short = True
    startup_candle_count = 400
    process_only_new_candles = True

    minimal_roi = {"0": 0.10}
    stoploss = -0.20
    trailing_stop = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    DEFAULT_GENES: Dict[str, Any] = dict(DEFAULT_GENES)
    BTC_FILTER_PAIR = "BTC/USDT"

    @property
    def genes(self) -> Dict[str, Any]:
        return dict(self.DEFAULT_GENES)

    def informative_pairs(self) -> List[Tuple[str, str]]:
        pairs: List[str] = []
        if getattr(self, "dp", None) is not None:
            pairs = list(self.dp.current_whitelist())

        informative_pairs: List[Tuple[str, str]] = []
        seen = set()

        for pair in pairs:
            for timeframe in ("1h", "4h"):
                item = (pair, timeframe)
                if item not in seen:
                    informative_pairs.append(item)
                    seen.add(item)

        for timeframe in ("1h", "4h"):
            btc_item = (self.BTC_FILTER_PAIR, timeframe)
            if btc_item not in seen:
                informative_pairs.append(btc_item)
                seen.add(btc_item)

        return informative_pairs

    def _get_informative_dataframe(self, pair: str, timeframe: str) -> DataFrame:
        if getattr(self, "dp", None) is None:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
        return self.dp.get_pair_dataframe(pair=pair, timeframe=timeframe)

    def _compute_pair_informative(self, pair: str, timeframe: str, suffix: str) -> DataFrame:
        genes = self.genes
        period = int(genes[f"bb_period_{suffix}"])
        std_dev = float(genes[f"bb_std_{suffix}"])
        informative = self._get_informative_dataframe(pair, timeframe).copy()
        if informative.empty:
            return informative
        return compute_bollinger_features(
            informative,
            period=period,
            std_dev=std_dev,
            suffix=suffix,
        )

    def _compute_btc_filter(self, timeframe: str, suffix: str) -> DataFrame:
        genes = self.genes
        period = int(genes[f"bb_period_{suffix}"])
        std_dev = float(genes[f"bb_std_{suffix}"])
        btc = self._get_informative_dataframe(self.BTC_FILTER_PAIR, timeframe).copy()
        if btc.empty:
            return btc

        btc = compute_bollinger_features(
            btc,
            period=period,
            std_dev=std_dev,
            suffix=suffix,
        )
        rename_map = {
            f"bb_mid_{suffix}": f"btc_bb_mid_{suffix}",
            f"bb_mid_slope_{suffix}": f"btc_bb_mid_slope_{suffix}",
            f"rsi_{suffix}": f"btc_rsi_{suffix}",
        }
        return btc.rename(columns=rename_map)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        genes = self.genes
        pair = metadata.get("pair", self.BTC_FILTER_PAIR)

        df = compute_bollinger_features(
            dataframe.copy(),
            period=int(genes["bb_period_15m"]),
            std_dev=float(genes["bb_std_15m"]),
            suffix="15m",
        )

        pair_1h = self._compute_pair_informative(pair, "1h", "1h")
        pair_4h = self._compute_pair_informative(pair, "4h", "4h")
        btc_1h = self._compute_btc_filter("1h", "1h")
        btc_4h = self._compute_btc_filter("4h", "4h")

        pair_1h_columns = [
            "bb_mid_1h",
            "bb_upper_1h",
            "bb_lower_1h",
            "bb_width_1h",
            "bb_percent_b_1h",
            "bb_mid_slope_1h",
            "atr_1h",
            "rsi_1h",
            "volume_mean_1h",
        ]
        pair_4h_columns = [
            "bb_mid_4h",
            "bb_upper_4h",
            "bb_lower_4h",
            "bb_width_4h",
            "bb_percent_b_4h",
            "bb_mid_slope_4h",
            "atr_4h",
            "rsi_4h",
            "volume_mean_4h",
        ]
        btc_1h_columns = [
            "btc_bb_mid_1h",
            "btc_bb_mid_slope_1h",
            "btc_rsi_1h",
        ]
        btc_4h_columns = [
            "btc_bb_mid_4h",
            "btc_bb_mid_slope_4h",
            "btc_rsi_4h",
        ]

        df = merge_informative_features(df, pair_1h, pair_1h_columns)
        df = merge_informative_features(df, pair_4h, pair_4h_columns)
        df = merge_informative_features(df, btc_1h, btc_1h_columns)
        df = merge_informative_features(df, btc_4h, btc_4h_columns)
        df = compute_resonance_scores(df, genes)
        return df

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return apply_entry_logic(dataframe, self.genes)

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return apply_exit_logic(dataframe)

    def _latest_analyzed_row(self, pair: str) -> Dict[str, Any]:
        if getattr(self, "dp", None) is None:
            return {}

        analyzed = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        if isinstance(analyzed, tuple):
            analyzed = analyzed[0]
        if analyzed is None or analyzed.empty:
            return {}
        return analyzed.tail(1).to_dict("records")[0]

    def _score_from_row(self, row: Dict[str, Any], side: str | None) -> float:
        if str(side or "long").lower() == "short":
            return float(row.get("resonance_short_score", 0.0) or 0.0)
        return float(row.get("resonance_long_score", 0.0) or 0.0)

    def _four_hour_regime_ok(self, row: Dict[str, Any], side: str | None) -> bool:
        close = float(row.get("close", 0.0) or 0.0)
        bb_mid = float(row.get("bb_mid_4h", close) or close)
        slope = float(row.get("bb_mid_slope_4h", 0.0) or 0.0)
        if str(side or "long").lower() == "short":
            return close <= bb_mid and slope <= 0.0
        return close >= bb_mid and slope >= 0.0

    def _trade_side(self, trade: Any) -> str:
        return "short" if bool(getattr(trade, "is_short", False)) else "long"

    def custom_stake_amount(
        self,
        pair: str,
        current_time: Any,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None = None,
        max_stake: float | None = None,
        leverage: float = 1.0,
        entry_tag: str | None = None,
        side: str = "long",
        **kwargs: Any,
    ) -> float:
        row = self._latest_analyzed_row(pair)
        if not row:
            return 0.0

        genes = self.genes
        score = self._score_from_row(row, side)
        atr = float(row.get("atr_15m", 0.0) or 0.0)
        rate = float(current_rate or row.get("close", 0.0) or 0.0)
        stop_distance_ratio = 0.0
        if rate > 0.0 and atr > 0.0:
            stop_distance_ratio = (atr * float(genes["atr_stop_mult"])) / rate

        return calculate_stake_amount(
            available_stake=proposed_stake,
            score=score,
            stop_distance_ratio=stop_distance_ratio,
            genes=genes,
            min_stake=min_stake,
            max_stake=max_stake,
        )

    def adjust_trade_position(
        self,
        trade: Any,
        current_time: Any,
        current_rate: float,
        current_profit: float,
        min_stake: float | None = None,
        max_stake: float | None = None,
        current_entry_rate: float | None = None,
        current_exit_rate: float | None = None,
        current_entry_profit: float | None = None,
        current_exit_profit: float | None = None,
        **kwargs: Any,
    ) -> float | None:
        pair = getattr(trade, "pair", "")
        row = self._latest_analyzed_row(pair)
        if not row:
            return None

        side = self._trade_side(trade)
        score = self._score_from_row(row, side)
        current_stake = float(getattr(trade, "stake_amount", 0.0) or 0.0)
        successful_entries = int(getattr(trade, "nr_of_successful_entries", 1) or 1)
        successful_exits = int(getattr(trade, "nr_of_successful_exits", 0) or 0)
        raw_has_open_orders = getattr(trade, "has_open_orders", False)
        has_open_orders = bool(
            raw_has_open_orders() if callable(raw_has_open_orders) else raw_has_open_orders
        )

        reduce_action = should_reduce_position(score, already_reduced=successful_exits > 0)
        if reduce_action == "exit":
            return -current_stake
        if reduce_action == "reduce_half":
            return -(current_stake * 0.5)

        dca_stake = calculate_dca_stake(
            current_stake=current_stake,
            score=score,
            current_profit=current_profit,
            successful_entries=successful_entries,
            has_open_orders=has_open_orders,
            four_hour_regime_ok=self._four_hour_regime_ok(row, side),
            genes=self.genes,
        )
        if dca_stake is None:
            return None
        if max_stake is not None:
            dca_stake = min(dca_stake, float(max_stake))
        return dca_stake

    def custom_stoploss(
        self,
        pair: str,
        trade: Any,
        current_time: Any,
        current_rate: float,
        current_profit: float,
        **kwargs: Any,
    ) -> float:
        genes = self.genes
        row = self._latest_analyzed_row(pair)
        atr = float(row.get("atr_15m", 0.0) or 0.0) if row else 0.0
        return calculate_stoploss_from_atr(
            atr=atr,
            current_rate=current_rate,
            atr_stop_mult=float(genes["atr_stop_mult"]),
            max_position_risk=float(genes["max_position_risk"]),
        )

    def leverage(
        self,
        pair: str,
        current_time: Any,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None = None,
        side: str = "long",
        **kwargs: Any,
    ) -> float:
        row = self._latest_analyzed_row(pair)
        score = self._score_from_row(row, side) if row else 0.0
        trading_mode = kwargs.get("trading_mode")
        if trading_mode is None:
            config = getattr(self, "config", {}) or {}
            trading_mode = config.get("trading_mode", "spot")
        return calculate_leverage(score, max_leverage, trading_mode, self.genes)
