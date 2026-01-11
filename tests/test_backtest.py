import unittest
from unittest.mock import patch, MagicMock
from strategy.backtest import render_strategy

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

if __name__ == '__main__':
    unittest.main()