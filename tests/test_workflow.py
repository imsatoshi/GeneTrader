import unittest
from unittest.mock import patch, MagicMock
from scripts.workflow import TradeWorkflow

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

if __name__ == '__main__':
    unittest.main()