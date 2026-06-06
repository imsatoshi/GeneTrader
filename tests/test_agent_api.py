"""Unit tests for agent API module."""

import json
import os
import shutil
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import http.client

from agent_api.auth import AuthManager, APIKey, APIKeyAuth
from agent_api.websocket_manager import (
    WebSocketManager, WebSocketMessage, MessageType, WebSocketConnection
)
from agent_api.api_server import AgentAPI, AgentAPIHandler, APIResponse


class TestAuthManager(unittest.TestCase):
    """Tests for AuthManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.auth = AuthManager(master_key='test-master-key')

    def test_master_key_validation(self):
        """Test master key validation."""
        key = self.auth.validate_key('test-master-key')

        self.assertIsNotNone(key)
        self.assertEqual(key.key_id, 'master')
        self.assertIn('*', key.permissions)

    def test_invalid_key(self):
        """Test invalid key rejection."""
        key = self.auth.validate_key('invalid-key')
        self.assertIsNone(key)

    def test_generate_key(self):
        """Test key generation."""
        raw_key, api_key = self.auth.generate_key(
            name='Test Agent',
            permissions=['read', 'write'],
            expires_days=30
        )

        self.assertIsNotNone(raw_key)
        self.assertEqual(api_key.name, 'Test Agent')
        self.assertIn('read', api_key.permissions)
        self.assertIn('write', api_key.permissions)
        self.assertIsNotNone(api_key.expires_at)

    def test_validate_generated_key(self):
        """Test validating a generated key."""
        raw_key, _ = self.auth.generate_key('Test Key')

        validated = self.auth.validate_key(raw_key)

        self.assertIsNotNone(validated)
        self.assertEqual(validated.name, 'Test Key')

    def test_check_permission(self):
        """Test permission checking."""
        _, api_key = self.auth.generate_key('Test', permissions=['read'])

        self.assertTrue(self.auth.check_permission(api_key, 'read'))
        self.assertFalse(self.auth.check_permission(api_key, 'write'))

    def test_master_key_all_permissions(self):
        """Test master key has all permissions."""
        master_key = self.auth.validate_key('test-master-key')

        self.assertTrue(self.auth.check_permission(master_key, 'read'))
        self.assertTrue(self.auth.check_permission(master_key, 'write'))
        self.assertTrue(self.auth.check_permission(master_key, 'admin'))

    def test_rate_limiting(self):
        """Test rate limiting."""
        auth = AuthManager(master_key='key', rate_limit_per_minute=5)

        # Should allow first 5 requests
        for _ in range(5):
            self.assertTrue(auth.check_rate_limit('master'))

        # 6th request should be denied
        self.assertFalse(auth.check_rate_limit('master'))

    def test_revoke_key(self):
        """Test key revocation."""
        raw_key, api_key = self.auth.generate_key('To Revoke')

        # Key should work
        self.assertIsNotNone(self.auth.validate_key(raw_key))

        # Revoke
        self.assertTrue(self.auth.revoke_key(api_key.key_id))

        # Key should no longer work
        self.assertIsNone(self.auth.validate_key(raw_key))

    def test_list_keys(self):
        """Test listing keys."""
        self.auth.generate_key('Key 1')
        self.auth.generate_key('Key 2')

        keys = self.auth.list_keys()

        # Should have master + 2 generated
        self.assertEqual(len(keys), 3)

    def test_expired_key(self):
        """Test expired key rejection."""
        raw_key, api_key = self.auth.generate_key('Expiring', expires_days=0)

        # Manually set expiration to past
        api_key.expires_at = datetime.now() - timedelta(days=1)

        validated = self.auth.validate_key(raw_key)
        self.assertIsNone(validated)


class TestAPIKeyAuth(unittest.TestCase):
    """Tests for APIKeyAuth dependency."""

    def setUp(self):
        """Set up test fixtures."""
        self.auth_manager = AuthManager(master_key='test-key')

    def test_call_valid_key(self):
        """Test valid key authentication."""
        auth = APIKeyAuth(self.auth_manager)
        result = auth('test-key')

        self.assertIsNotNone(result)

    def test_call_invalid_key(self):
        """Test invalid key rejection."""
        auth = APIKeyAuth(self.auth_manager)
        result = auth('invalid')

        self.assertIsNone(result)

    def test_permission_check(self):
        """Test permission-based authentication."""
        raw_key, _ = self.auth_manager.generate_key('Read Only', permissions=['read'])

        auth_read = APIKeyAuth(self.auth_manager, required_permission='read')
        auth_write = APIKeyAuth(self.auth_manager, required_permission='write')

        # Should pass read check
        self.assertIsNotNone(auth_read(raw_key))

        # Should fail write check
        self.assertIsNone(auth_write(raw_key))


class TestWebSocketMessage(unittest.TestCase):
    """Tests for WebSocketMessage."""

    def test_to_json(self):
        """Test JSON serialization."""
        msg = WebSocketMessage(
            type=MessageType.METRICS_UPDATE,
            data={'profit': 100.0},
            strategy_name='TestStrategy'
        )

        json_str = msg.to_json()
        data = json.loads(json_str)

        self.assertEqual(data['type'], 'metrics_update')
        self.assertEqual(data['data']['profit'], 100.0)
        self.assertEqual(data['strategy_name'], 'TestStrategy')

    def test_from_json(self):
        """Test JSON deserialization."""
        json_str = json.dumps({
            'type': 'alert',
            'data': {'severity': 'high'},
            'timestamp': datetime.now().isoformat(),
            'strategy_name': 'TestStrategy',
        })

        msg = WebSocketMessage.from_json(json_str)

        self.assertEqual(msg.type, MessageType.ALERT)
        self.assertEqual(msg.data['severity'], 'high')


class TestWebSocketManager(unittest.TestCase):
    """Tests for WebSocketManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = WebSocketManager(heartbeat_interval=60)
        self.sent_messages = []

        async def mock_send(msg):
            self.sent_messages.append(msg)

        self.mock_send = mock_send

    def test_add_connection(self):
        """Test adding a connection."""
        conn = self.manager.add_connection(
            'conn_1',
            'api_key_1',
            self.mock_send
        )

        self.assertEqual(conn.connection_id, 'conn_1')
        self.assertEqual(self.manager.get_connection_count(), 1)

    def test_remove_connection(self):
        """Test removing a connection."""
        self.manager.add_connection('conn_1', 'api_key_1', self.mock_send)
        self.manager.remove_connection('conn_1')

        self.assertEqual(self.manager.get_connection_count(), 0)

    def test_subscribe(self):
        """Test topic subscription."""
        self.manager.add_connection('conn_1', 'api_key_1', self.mock_send)
        result = self.manager.subscribe('conn_1', 'metrics:TestStrategy')

        self.assertTrue(result)
        self.assertIn('metrics:TestStrategy', self.manager._topic_subscribers)

    def test_unsubscribe(self):
        """Test topic unsubscription."""
        self.manager.add_connection(
            'conn_1', 'api_key_1', self.mock_send,
            subscriptions={'metrics:TestStrategy'}
        )
        result = self.manager.unsubscribe('conn_1', 'metrics:TestStrategy')

        self.assertTrue(result)

    def test_get_connections_info(self):
        """Test getting connection info."""
        self.manager.add_connection('conn_1', 'api_key_1', self.mock_send)
        self.manager.add_connection('conn_2', 'api_key_2', self.mock_send)

        info = self.manager.get_connections_info()

        self.assertEqual(len(info), 2)


class TestWebSocketBroadcast(unittest.TestCase):
    """Tests for WebSocket broadcast functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = WebSocketManager()
        self.received = {'conn_1': [], 'conn_2': []}

        async def make_send(conn_id):
            async def send(msg):
                self.received[conn_id].append(msg)
            return send

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up."""
        self.loop.close()

    def test_broadcast_to_all(self):
        """Test broadcasting to all connections."""
        async def run_test():
            await_sends = []

            async def send1(msg):
                self.received['conn_1'].append(msg)

            async def send2(msg):
                self.received['conn_2'].append(msg)

            self.manager.add_connection('conn_1', 'key_1', send1)
            self.manager.add_connection('conn_2', 'key_2', send2)

            msg = WebSocketMessage(
                type=MessageType.ALERT,
                data={'test': True}
            )

            count = await self.manager.broadcast(msg)
            return count

        count = self.loop.run_until_complete(run_test())

        self.assertEqual(count, 2)
        self.assertEqual(len(self.received['conn_1']), 1)
        self.assertEqual(len(self.received['conn_2']), 1)

    def test_broadcast_to_topic(self):
        """Test broadcasting to specific topic."""
        async def run_test():
            async def send1(msg):
                self.received['conn_1'].append(msg)

            async def send2(msg):
                self.received['conn_2'].append(msg)

            self.manager.add_connection(
                'conn_1', 'key_1', send1,
                subscriptions={'metrics:Strategy1'}
            )
            self.manager.add_connection(
                'conn_2', 'key_2', send2,
                subscriptions={'metrics:Strategy2'}
            )

            msg = WebSocketMessage(
                type=MessageType.METRICS_UPDATE,
                data={'test': True}
            )

            count = await self.manager.broadcast(msg, 'metrics:Strategy1')
            return count

        count = self.loop.run_until_complete(run_test())

        # Only conn_1 should receive
        self.assertEqual(count, 1)
        self.assertEqual(len(self.received['conn_1']), 1)
        self.assertEqual(len(self.received['conn_2']), 0)


class TestAPIResponse(unittest.TestCase):
    """Tests for APIResponse."""

    def test_success_response(self):
        """Test successful response."""
        response = APIResponse(
            success=True,
            data={'key': 'value'}
        )

        json_str = response.to_json()
        data = json.loads(json_str)

        self.assertTrue(data['success'])
        self.assertEqual(data['data']['key'], 'value')
        self.assertIsNone(data['error'])

    def test_error_response(self):
        """Test error response."""
        response = APIResponse(
            success=False,
            error='Something went wrong',
            status_code=500
        )

        json_str = response.to_json()
        data = json.loads(json_str)

        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Something went wrong')


class TestAgentAPI(unittest.TestCase):
    """Tests for AgentAPI server."""

    def setUp(self):
        """Set up test fixtures."""
        self.api = AgentAPI(
            host='127.0.0.1',
            port=8099,
            api_key='test-api-key-123456'
        )

    def test_initialization(self):
        """Test API initialization."""
        self.assertEqual(self.api.host, '127.0.0.1')
        self.assertEqual(self.api.port, 8099)
        self.assertIsNotNone(self.api.auth_manager)

    def test_requires_strong_api_key(self):
        """Test API refuses missing or weak master keys."""
        for key in (None, '', 'default-key', 'short-key'):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    AgentAPI(host='127.0.0.1', port=0, api_key=key)

    def test_header_auth_query_key_rejected_and_cors_allowlisted(self):
        """Test API accepts header auth but rejects query-string API keys."""
        api = AgentAPI(
            host='127.0.0.1',
            port=0,
            api_key='test-api-key-123456',
            cors_allowed_origins=('http://localhost:5173',),
        )
        api.start()
        port = api._server.server_port

        try:
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
            conn.request(
                'GET',
                '/api/v1/status',
                headers={
                    'X-API-Key': 'test-api-key-123456',
                    'Origin': 'http://localhost:5173',
                },
            )
            response = conn.getresponse()
            response.read()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader('Access-Control-Allow-Origin'), 'http://localhost:5173')
            conn.close()

            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
            conn.request('GET', '/api/v1/status?api_key=test-api-key-123456')
            response = conn.getresponse()
            response.read()
            self.assertEqual(response.status, 401)
            self.assertIsNone(response.getheader('Access-Control-Allow-Origin'))
            conn.close()

            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
            conn.request('GET', '/api/v1/health')
            response = conn.getresponse()
            response.read()
            self.assertEqual(response.status, 200)
            conn.close()
        finally:
            api.stop()

    def test_internal_errors_are_not_echoed_to_client(self):
        """Test server errors do not expose internal exception details."""
        optimizer = MagicMock()
        optimizer.get_status.side_effect = RuntimeError("C:/Users/name/.env api_key=abc")
        api = AgentAPI(
            host='127.0.0.1',
            port=0,
            api_key='test-api-key-123456',
            adaptive_optimizer=optimizer,
        )
        api.start()
        port = api._server.server_port

        try:
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
            conn.request('GET', '/api/v1/status', headers={'X-API-Key': 'test-api-key-123456'})
            response = conn.getresponse()
            body = response.read().decode()
            conn.close()

            self.assertEqual(response.status, 500)
            self.assertIn("Internal server error", body)
            self.assertNotIn("C:/Users", body)
            self.assertNotIn("api_key", body)
            self.assertNotIn("abc", body)
        finally:
            api.stop()

    def test_add_approval_request(self):
        """Test adding approval request."""
        self.api.add_approval_request(
            'req_123',
            'TestStrategy',
            'v5',
            {'profit': 0.15}
        )

        # Should be in pending approvals
        self.assertIn('req_123', AgentAPIHandler.approval_requests)

    def test_check_approval_pending(self):
        """Test checking pending approval."""
        self.api.add_approval_request(
            'req_456',
            'TestStrategy',
            'v5',
            {}
        )

        result = self.api.check_approval('req_456')

        self.assertIsNone(result)  # Still pending

    def test_check_approval_approved(self):
        """Test checking approved request."""
        self.api.add_approval_request('req_789', 'Test', 'v1', {})

        # Simulate approval
        AgentAPIHandler.approval_requests['req_789']['approved'] = True

        result = self.api.check_approval('req_789')

        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
