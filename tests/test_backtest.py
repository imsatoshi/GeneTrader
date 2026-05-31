import unittest
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from strategy.backtest import render_strategy, run_backtest

class TestBacktest(unittest.TestCase):

    @patch('strategy.backtest.generate_dynamic_template')
    def test_render_strategy(self, mock_generate_dynamic_template):
        # 模拟 generate_dynamic_template 的返回值
        # Note: params should be a list of dicts, not a dict
        mock_template = """
        class ${strategy_name}(IStrategy):
            buy_param = ${buy_param}
            sell_param = ${sell_param}
        """
        mock_params = [
            {'name': 'buy_param', 'type': 'Decimal', 'optimize': True, 'decimal_places': 1, 'start': 0.0, 'end': 100.0},
            {'name': 'sell_param', 'type': 'Int', 'optimize': True, 'start': 0, 'end': 100}
        ]
        mock_generate_dynamic_template.return_value = (mock_template, mock_params)

        print("Mock template:", mock_template)
        print("Mock params:", mock_params)

        # 测试参数
        test_params = [30.5, 70]
        test_strategy_name = "TestStrategy"

        print("Test params:", test_params)
        print("Test strategy name:", test_strategy_name)

        # 调用被测试的函数
        result = render_strategy(test_params, test_strategy_name)

        print("Rendered result:", result)

        # 验证结果
        expected_result = """
        class TestStrategy(IStrategy):
            buy_param = 30.5
            sell_param = 70
        """
        print("Expected result:", expected_result)

        self.assertEqual(result.strip(), expected_result.strip())

        # 验证 generate_dynamic_template 被正确调用
        mock_generate_dynamic_template.assert_called_once()
        print("generate_dynamic_template called:", mock_generate_dynamic_template.called)

    def test_run_backtest_removes_temporary_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            user_dir = root / 'user_data'
            strategy_dir = user_dir / 'strategies'
            results_dir = root / 'results'
            data_dir = root / 'data'
            for path in (user_dir, strategy_dir, results_dir, data_dir):
                path.mkdir(parents=True, exist_ok=True)
            (user_dir / 'config.json').write_text(json.dumps({
                'timeframe': '5m',
                'exchange': {'pair_whitelist': ['BTC/USDT']},
            }), encoding='utf-8')
            fake_settings = SimpleNamespace(
                strategy_dir=str(strategy_dir),
                user_dir=str(user_dir),
                add_dynamic_timeframes=False,
                add_max_open_trades=False,
                results_dir=str(results_dir),
                freqtrade_path='freqtrade',
                data_dir=str(data_dir),
                max_retries=1,
                retry_delay=0,
                backtest_timerange_weeks=1,
            )

            with patch('strategy.backtest.settings', fake_settings), \
                    patch('strategy.backtest.render_strategy', return_value='class S: pass'), \
                    patch('strategy.backtest.subprocess.run', return_value=SimpleNamespace(returncode=0)), \
                    patch('strategy.backtest.parse_backtest_results', return_value={'total_trades': 1}), \
                    patch('strategy.backtest.fitness_function', return_value=42.0), \
                    patch('strategy.backtest.time.time', return_value=12345), \
                    patch('strategy.backtest.random.randint', return_value=6789):
                result = run_backtest([1, 2, 3], ['BTC/USDT'], generation=1)

            self.assertEqual(result, 42.0)
            self.assertEqual(list(user_dir.glob('temp_config_*.json')), [])

if __name__ == '__main__':
    unittest.main()
