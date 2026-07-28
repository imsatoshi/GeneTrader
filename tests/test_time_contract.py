"""Timezone contract tests.

Mixing aware and naive datetimes raises TypeError at runtime, and mixing local
and UTC naive values silently shifts every metrics window by the host offset.
The live monitoring path crossed both boundaries: Freqtrade returns UTC with an
offset while the window bound came from a naive ``datetime.now()``.
"""

import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from monitoring.freqtrade_client import Trade
from monitoring.performance_db import PerformanceDB, PerformanceSnapshot
from utils.time_utils import parse_utc, to_utc, utc_iso, utc_now


class TestTimeUtils(unittest.TestCase):
    def test_utc_now_is_aware(self):
        self.assertIsNotNone(utc_now().tzinfo)

    def test_to_utc_treats_naive_as_utc(self):
        naive = datetime(2026, 7, 29, 12, 0, 0)
        self.assertEqual(to_utc(naive).hour, 12)
        self.assertEqual(to_utc(naive).tzinfo, timezone.utc)

    def test_to_utc_converts_offset(self):
        shanghai = datetime(2026, 7, 29, 20, 0, 0, tzinfo=timezone(timedelta(hours=8)))
        self.assertEqual(to_utc(shanghai).hour, 12)

    def test_parse_utc_handles_z_offset_and_naive(self):
        for text in ('2026-07-29T12:00:00Z',
                     '2026-07-29T12:00:00+00:00',
                     '2026-07-29T12:00:00'):
            parsed = parse_utc(text)
            self.assertIsNotNone(parsed.tzinfo, text)
            self.assertEqual(parsed.hour, 12, text)

    def test_parse_utc_tolerates_garbage(self):
        self.assertIsNone(parse_utc('not-a-date'))
        self.assertIsNone(parse_utc(None))

    def test_utc_iso_is_offset_free_and_sorts_lexically(self):
        early = utc_iso(datetime(2026, 7, 29, 2, 0, tzinfo=timezone.utc))
        late = utc_iso(datetime(2026, 7, 29, 10, 0, tzinfo=timezone.utc))
        self.assertNotIn('+', early)
        self.assertLess(early, late)

    def test_utc_iso_normalises_before_formatting(self):
        shanghai = datetime(2026, 7, 29, 10, 0, tzinfo=timezone(timedelta(hours=8)))
        utc = datetime(2026, 7, 29, 2, 0, tzinfo=timezone.utc)
        self.assertEqual(utc_iso(shanghai), utc_iso(utc))


class TestFreqtradeTradeParsing(unittest.TestCase):
    """API timestamps must be comparable with the monitor's window bound."""

    def _trade(self, payload):
        base = {'trade_id': 1, 'pair': 'BTC/USDT', 'is_open': False,
                'open_rate': 100.0, 'profit_ratio': 0.01}
        base.update(payload)
        return Trade.from_api_response(base)

    def test_dates_are_aware_regardless_of_api_format(self):
        for value in ('2026-07-29T12:00:00Z',
                      '2026-07-29T12:00:00+00:00',
                      '2026-07-29T12:00:00'):
            trade = self._trade({'open_date': value, 'close_date': value})
            self.assertIsNotNone(trade.open_date.tzinfo, value)
            self.assertIsNotNone(trade.close_date.tzinfo, value)

    def test_trade_dates_compare_against_window_bound(self):
        # This raised TypeError before timestamps were normalised.
        trade = self._trade({'open_date': '2026-07-29T12:00:00+00:00'})
        since = utc_now() - timedelta(hours=168)
        self.assertIsInstance(trade.open_date >= since, bool)

    def test_missing_open_date_falls_back_to_aware_now(self):
        self.assertIsNotNone(self._trade({}).open_date.tzinfo)
        self.assertIsNone(self._trade({}).close_date)


class TestPerformanceDBWindow(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db = PerformanceDB(os.path.join(self.temp_dir, 'perf.db'))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _snapshot(self, timestamp):
        return PerformanceSnapshot(
            timestamp=timestamp, strategy_name='S', total_profit=1.0,
            total_profit_pct=0.01, win_rate=0.5, total_trades=10,
            winning_trades=5, losing_trades=5, avg_profit_per_trade=1.0,
            avg_duration_minutes=60.0, max_drawdown=0.1, profit_factor=1.2,
        )

    def test_rolling_window_boundary_is_exact(self):
        now = utc_now()
        for hours in (1, 100, 167, 169, 400):
            self.db.save_snapshot(self._snapshot(now - timedelta(hours=hours)))

        within = self.db.get_rolling_metrics('S', window_hours=168)
        self.assertEqual(len(within), 3)

    def test_round_trip_preserves_awareness(self):
        self.db.save_snapshot(self._snapshot(utc_now() - timedelta(hours=1)))
        loaded = self.db.get_rolling_metrics('S', window_hours=168)
        self.assertIsNotNone(loaded[0].timestamp.tzinfo)

    def test_offset_input_lands_in_the_same_window_as_utc(self):
        """A caller passing +08:00 must not shift the window by 8 hours."""
        now_utc = utc_now()
        shanghai = timezone(timedelta(hours=8))
        self.db.save_snapshot(self._snapshot((now_utc - timedelta(hours=1)).astimezone(shanghai)))
        self.assertEqual(len(self.db.get_rolling_metrics('S', window_hours=168)), 1)
        self.assertEqual(len(self.db.get_rolling_metrics('S', window_hours=0)), 0)


if __name__ == '__main__':
    unittest.main()
