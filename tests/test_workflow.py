import unittest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from scripts.workflow import TradeWorkflow, redact_sensitive_config

class TestTradeWorkflow(unittest.TestCase):

    @patch('scripts.workflow.subprocess.run')
    def test_upload_to_server_success(self, mock_subprocess_run):
        # Arrange
        mock_subprocess_run.return_value.returncode = 0  # Simulate successful subprocess call
        workflow = TradeWorkflow('ga.json')
        workflow.remote_server = {
            'key_path': '/path/to/key',
            'port': 22,
            'username': 'user',
            'hostname': 'host',
            'remote_datadir': '/remote/data/dir',
            'remote_strategydir': '/remote/strategy/dir'
        }

        # Act
        result = workflow.upload_to_server()

        # Assert
        self.assertTrue(result)
        self.assertEqual(mock_subprocess_run.call_count, 2)  # Ensure both scp commands were called

    @patch('scripts.workflow.subprocess.run')
    def test_upload_to_server_failure(self, mock_subprocess_run):
        # Arrange
        mock_subprocess_run.return_value.returncode = 1  # Simulate failed subprocess call
        workflow = TradeWorkflow('ga.json')
        workflow.remote_server = {
            'key_path': '/path/to/key',
            'port': 22,
            'username': 'user',
            'hostname': 'host',
            'remote_datadir': '/remote/data/dir',
            'remote_strategydir': '/remote/strategy/dir'
        }

        # Act
        result = workflow.upload_to_server()

        # Assert
        self.assertFalse(result)
        self.assertEqual(mock_subprocess_run.call_count, 1)  # Ensure at least one scp command was called

    def test_restart_trading_rest_uses_freqtrade_credentials(self):
        workflow = TradeWorkflow('ga.json')
        workflow.remote_server = {
            'api_url': 'http://freqtrade.local/api/v1',
            'freqtrade_username': 'freqtrade-user',
            'freqtrade_password': 'freqtrade-pass',
            'username': 'ssh-user',
            'hostname': 'host',
            'port': 22,
            'key_path': '/path/to/key',
        }

        with patch.object(workflow, 'restart_freqtrade', return_value=True) as restart:
            result = workflow.restart_trading(is_restful=True)

        self.assertTrue(result)
        restart.assert_called_once_with(
            'http://freqtrade.local/api/v1',
            'freqtrade-user',
            'freqtrade-pass',
        )

    def test_redact_sensitive_config_replaces_secret_values(self):
        config = {
            'exchange': {'key': 'exchange-key', 'secret': 'exchange-secret'},
            'api_server': {
                'jwt_secret_key': 'jwt-secret',
                'password': 'api-password',
                'username': 'safe-user',
            },
            'pair_whitelist': ['BTC/USDT'],
        }

        redacted = redact_sensitive_config(config)

        serialized = json.dumps(redacted)
        self.assertNotIn('exchange-key', serialized)
        self.assertNotIn('exchange-secret', serialized)
        self.assertNotIn('jwt-secret', serialized)
        self.assertNotIn('api-password', serialized)
        self.assertEqual(redacted['api_server']['username'], 'safe-user')

    def test_example_config_uses_secret_placeholders(self):
        example_path = Path(__file__).resolve().parents[1] / 'user_data' / 'example.json'
        config = json.loads(example_path.read_text(encoding='utf-8'))
        api_server = config['api_server']

        self.assertIn('PLACEHOLDER', api_server['jwt_secret_key'])
        self.assertIn('PLACEHOLDER', api_server['username'])
        self.assertIn('PLACEHOLDER', api_server['password'])
        self.assertNotEqual(api_server['password'], 'zhangjiawei')

    def test_save_best_to_daily_copies_redacted_config(self):
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                Path('logs').mkdir()
                Path('logs/fitness_log.txt').write_text('fitness=1.0', encoding='utf-8')
                Path('strategy.py').write_text('class Strategy: pass', encoding='utf-8')
                Path('results.txt').write_text('results', encoding='utf-8')
                Path('config.json').write_text(json.dumps({
                    'exchange': {'key': 'exchange-key', 'secret': 'exchange-secret'},
                    'api_server': {'password': 'api-password', 'jwt_secret_key': 'jwt-secret'},
                }), encoding='utf-8')

                workflow = TradeWorkflow('ga.json')
                self.assertTrue(
                    workflow.save_best_to_daily('gen1', 'results.txt', 'config.json', 'strategy.py')
                )

                copied_config = next(Path('daily_results').rglob('config.json'))
                payload = copied_config.read_text(encoding='utf-8')
                self.assertNotIn('exchange-key', payload)
                self.assertNotIn('exchange-secret', payload)
                self.assertNotIn('api-password', payload)
                self.assertNotIn('jwt-secret', payload)
                self.assertIn('__REDACTED__', payload)
            finally:
                os.chdir(original_cwd)

if __name__ == '__main__':
    unittest.main()
