"""Regression tests for Agent API and rollback safety invariants.

These pin down behaviour that has been silently reverted before: permission
and rate-limit gates on read endpoints, a rollback endpoint that actually
rolls back, and a rollback manager that never reports success without
restoring the strategy file.
"""

import http.client
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from agent_api.api_server import AgentAPI
from deployment.rollback_manager import RollbackManager, RollbackConfig, RollbackReason
from deployment.version_control import StrategyVersionControl

STRONG_KEY = 'test-api-key-123456'


class TestReadEndpointGates(unittest.TestCase):
    """GET endpoints must check permission and rate limit, not just identity."""

    def setUp(self):
        self.api = AgentAPI(host='127.0.0.1', port=0, api_key=STRONG_KEY)
        self.api.start()
        self.port = self.api._server.server_port

    def tearDown(self):
        self.api.stop()

    def _get(self, path, key=STRONG_KEY):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        headers = {'X-API-Key': key} if key else {}
        conn.request('GET', path, headers=headers)
        response = conn.getresponse()
        response.read()
        conn.close()
        return response.status

    def test_write_only_key_cannot_read(self):
        raw_key, _ = self.api.auth_manager.generate_key('writer', permissions=['write'])
        self.assertEqual(self._get('/api/v1/status', key=raw_key), 403)

    def test_read_key_is_rate_limited(self):
        self.api.auth_manager.rate_limit_per_minute = 2
        raw_key, _ = self.api.auth_manager.generate_key('reader', permissions=['read'])
        statuses = [self._get('/api/v1/status', key=raw_key) for _ in range(4)]
        self.assertIn(429, statuses)

    def test_health_is_public_but_status_is_not(self):
        self.assertEqual(self._get('/api/v1/health', key=None), 200)
        self.assertEqual(self._get('/api/v1/status', key=None), 401)


class TestRollbackEndpointIsReal(unittest.TestCase):
    """The rollback endpoint must not report success without doing the work."""

    def _post_rollback(self, api):
        port = api._server.server_port
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
        conn.request(
            'POST', '/api/v1/rollback',
            body='{"strategy_name": "TestStrategy"}',
            headers={'X-API-Key': STRONG_KEY, 'Content-Type': 'application/json'},
        )
        response = conn.getresponse()
        body = response.read().decode()
        conn.close()
        return response.status, body

    def test_rollback_delegates_to_deployer(self):
        optimizer = MagicMock()
        optimizer.deployer.rollback.return_value = True
        api = AgentAPI(host='127.0.0.1', port=0, api_key=STRONG_KEY,
                       adaptive_optimizer=optimizer)
        api.start()
        try:
            status, _ = self._post_rollback(api)
        finally:
            api.stop()

        self.assertEqual(status, 200)
        optimizer.deployer.rollback.assert_called_once_with('TestStrategy', None)

    def test_failed_rollback_is_reported_as_failure(self):
        optimizer = MagicMock()
        optimizer.deployer.rollback.return_value = False
        api = AgentAPI(host='127.0.0.1', port=0, api_key=STRONG_KEY,
                       adaptive_optimizer=optimizer)
        api.start()
        try:
            status, _ = self._post_rollback(api)
        finally:
            api.stop()

        self.assertEqual(status, 500)

    def test_rollback_without_optimizer_is_not_faked(self):
        api = AgentAPI(host='127.0.0.1', port=0, api_key=STRONG_KEY)
        api.start()
        try:
            status, body = self._post_rollback(api)
        finally:
            api.stop()

        self.assertEqual(status, 501)
        self.assertNotIn('"success": true', body)


class TestRollbackManagerNeverFakesSuccess(unittest.TestCase):
    """Without a deploy callback the strategy file is never restored."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.vc = StrategyVersionControl(os.path.join(self.temp_dir, 'versions'))
        self.strategy_file = os.path.join(self.temp_dir, 'strategy.py')
        with open(self.strategy_file, 'w') as f:
            f.write("class TestStrategy:\n    pass\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _manager(self, **config_kwargs):
        return RollbackManager(
            self.vc,
            config=RollbackConfig(enabled=True, cooldown_minutes=0, **config_kwargs),
            rollback_history_file=os.path.join(self.temp_dir, 'history.json'),
        )

    def test_missing_deploy_callback_records_failure(self):
        v1 = self.vc.create_version('TestStrategy', self.strategy_file)
        v2 = self.vc.create_version('TestStrategy', self.strategy_file)
        self.vc.set_active('TestStrategy', v1.version_id)
        self.vc.set_active('TestStrategy', v2.version_id)

        manager = self._manager(require_confirmation=False)
        event = manager.execute_rollback('TestStrategy', reason=RollbackReason.MANUAL)

        self.assertIsNotNone(event)
        self.assertFalse(event.success)
        self.assertEqual(event.notes, 'deploy_callback_required')

    def test_confirmation_required_blocks_unattended_rollback(self):
        v1 = self.vc.create_version('TestStrategy', self.strategy_file)
        v2 = self.vc.create_version('TestStrategy', self.strategy_file)
        self.vc.set_active('TestStrategy', v1.version_id)
        self.vc.set_active('TestStrategy', v2.version_id)

        manager = self._manager(require_confirmation=True)
        manager.set_deploy_callback(lambda strategy, version: True)

        self.assertIsNone(manager.execute_rollback('TestStrategy', reason=RollbackReason.MANUAL))


if __name__ == '__main__':
    unittest.main()
