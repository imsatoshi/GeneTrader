"""
REST API server for AI agent integration.

Provides HTTP endpoints for AI agents to interact with the
GeneTrader optimization system.
"""

import json
import threading
from dataclasses import dataclass
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlparse
from utils.logging_config import logger

from agent_api.auth import AuthManager, APIKey
from agent_api.websocket_manager import WebSocketManager
from monitoring.performance_monitor import PerformanceMonitor
from monitoring.performance_db import PerformanceDB
from deployment.version_control import StrategyVersionControl
from deployment.strategy_deployer import StrategyDeployer
from adaptive.adaptive_optimizer import AdaptiveOptimizer
from adaptive.scheduler import OptimizationScheduler


@dataclass
class APIResponse:
    """Standard API response."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    status_code: int = 200

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps({
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'timestamp': datetime.now().isoformat(),
        })


class AgentAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for agent API."""

    # Class-level references to shared components
    auth_manager: Optional[AuthManager] = None
    performance_db: Optional[PerformanceDB] = None
    version_control: Optional[StrategyVersionControl] = None
    adaptive_optimizer: Optional[AdaptiveOptimizer] = None
    scheduler: Optional[OptimizationScheduler] = None
    approval_requests: Dict[str, Dict[str, Any]] = {}

    def log_message(self, format, *args):
        """Override to use custom logger."""
        logger.debug(f"API: {args[0]}")

    def _authenticate(self) -> Optional[APIKey]:
        """Authenticate the request."""
        if not self.auth_manager:
            return None

        # Get API key from header
        api_key_str = self.headers.get('X-API-Key', '')

        if not api_key_str:
            # Try query parameter
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            api_key_str = params.get('api_key', [''])[0]

        return self.auth_manager.validate_key(api_key_str)

    def _send_response(self, response: APIResponse) -> None:
        """Send API response."""
        self.send_response(response.status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response.to_json().encode())

    def _get_json_body(self) -> Optional[Dict[str, Any]]:
        """Parse JSON body from request."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                return json.loads(body.decode())
        except Exception as e:
            logger.error(f"Error parsing request body: {e}")
        return None

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-API-Key, Content-Type')
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        api_key = self._authenticate()
        if not api_key:
            self._send_response(APIResponse(
                success=False,
                error="Authentication required",
                status_code=401
            ))
            return

        if not self.auth_manager.check_permission(api_key, 'read'):
            self._send_response(APIResponse(
                success=False,
                error="Read permission required",
                status_code=403
            ))
            return

        if not self.auth_manager.check_rate_limit(api_key.key_id):
            self._send_response(APIResponse(
                success=False,
                error="Rate limit exceeded",
                status_code=429
            ))
            return

        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        try:
            if path == '/api/v1/health':
                self._handle_health()

            elif path == '/api/v1/status':
                self._handle_status()

            elif path == '/api/v1/metrics':
                self._handle_get_metrics(parsed)

            elif path == '/api/v1/versions':
                self._handle_get_versions(parsed)

            elif path == '/api/v1/optimization/status':
                self._handle_optimization_status()

            elif path == '/api/v1/scheduler/status':
                self._handle_scheduler_status()

            elif path == '/api/v1/approvals/pending':
                self._handle_pending_approvals()

            else:
                self._send_response(APIResponse(
                    success=False,
                    error=f"Endpoint not found: {path}",
                    status_code=404
                ))

        except Exception as e:
            logger.error(f"API error: {e}")
            self._send_response(APIResponse(
                success=False,
                error=str(e),
                status_code=500
            ))

    def do_POST(self):
        """Handle POST requests."""
        api_key = self._authenticate()
        if not api_key:
            self._send_response(APIResponse(
                success=False,
                error="Authentication required",
                status_code=401
            ))
            return

        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        # Check write permission
        if not self.auth_manager.check_permission(api_key, 'write'):
            self._send_response(APIResponse(
                success=False,
                error="Write permission required",
                status_code=403
            ))
            return

        if not self.auth_manager.check_rate_limit(api_key.key_id):
            self._send_response(APIResponse(
                success=False,
                error="Rate limit exceeded",
                status_code=429
            ))
            return

        try:
            if path == '/api/v1/optimization/trigger':
                self._handle_trigger_optimization()

            elif path == '/api/v1/deployment/approve':
                self._handle_approve_deployment()

            elif path == '/api/v1/deployment/reject':
                self._handle_reject_deployment()

            elif path == '/api/v1/rollback':
                self._handle_rollback()

            else:
                self._send_response(APIResponse(
                    success=False,
                    error=f"Endpoint not found: {path}",
                    status_code=404
                ))

        except Exception as e:
            logger.error(f"API error: {e}")
            self._send_response(APIResponse(
                success=False,
                error=str(e),
                status_code=500
            ))

    def _handle_health(self):
        """Health check endpoint."""
        self._send_response(APIResponse(
            success=True,
            data={
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
            }
        ))

    def _handle_status(self):
        """Get overall system status."""
        data = {
            'optimization': self.adaptive_optimizer.get_status() if self.adaptive_optimizer else None,
            'scheduler': self.scheduler.get_stats() if self.scheduler else None,
        }

        self._send_response(APIResponse(success=True, data=data))

    def _handle_get_metrics(self, parsed):
        """Get performance metrics."""
        params = parse_qs(parsed.query)
        strategy_name = params.get('strategy', [None])[0]
        hours = int(params.get('hours', [168])[0])

        if not self.performance_db:
            self._send_response(APIResponse(
                success=False,
                error="Performance database not available",
                status_code=503
            ))
            return

        from datetime import timedelta
        since = datetime.now() - timedelta(hours=hours)

        snapshots = self.performance_db.get_snapshots(
            strategy_name=strategy_name,
            since=since,
            limit=100
        )

        data = [
            {
                'timestamp': s.timestamp.isoformat(),
                'strategy': s.strategy_name,
                'profit_pct': s.total_profit_pct,
                'win_rate': s.win_rate,
                'total_trades': s.total_trades,
                'max_drawdown': s.max_drawdown,
                'profit_factor': s.profit_factor,
            }
            for s in snapshots
        ]

        self._send_response(APIResponse(success=True, data=data))

    def _handle_get_versions(self, parsed):
        """Get strategy versions."""
        params = parse_qs(parsed.query)
        strategy_name = params.get('strategy', [None])[0]

        if not self.version_control:
            self._send_response(APIResponse(
                success=False,
                error="Version control not available",
                status_code=503
            ))
            return

        if strategy_name:
            versions = self.version_control.get_all_versions(strategy_name)
            data = [
                {
                    'version_id': v.version_id,
                    'status': v.status.value,
                    'created_at': v.created_at.isoformat(),
                    'backtest_metrics': v.backtest_metrics,
                    'live_metrics': v.live_metrics,
                }
                for v in versions
            ]
        else:
            strategies = self.version_control.list_strategies()
            data = strategies

        self._send_response(APIResponse(success=True, data=data))

    def _handle_optimization_status(self):
        """Get optimization status."""
        if not self.adaptive_optimizer:
            self._send_response(APIResponse(
                success=False,
                error="Adaptive optimizer not available",
                status_code=503
            ))
            return

        data = {
            'status': self.adaptive_optimizer.get_status(),
            'history': self.adaptive_optimizer.get_optimization_history(10),
        }

        self._send_response(APIResponse(success=True, data=data))

    def _handle_scheduler_status(self):
        """Get scheduler status."""
        if not self.scheduler:
            self._send_response(APIResponse(
                success=False,
                error="Scheduler not available",
                status_code=503
            ))
            return

        data = {
            'stats': self.scheduler.get_stats(),
            'queue': self.scheduler.get_queue(),
            'running': self.scheduler.get_running(),
        }

        self._send_response(APIResponse(success=True, data=data))

    def _handle_pending_approvals(self):
        """Get pending approval requests."""
        data = list(self.approval_requests.values())
        self._send_response(APIResponse(success=True, data=data))

    def _handle_trigger_optimization(self):
        """Trigger manual optimization."""
        body = self._get_json_body() or {}
        strategy_name = body.get('strategy_name')
        reason = body.get('reason', 'manual_trigger')

        if not strategy_name:
            self._send_response(APIResponse(
                success=False,
                error="strategy_name required",
                status_code=400
            ))
            return

        if self.adaptive_optimizer:
            success = self.adaptive_optimizer.force_optimization(reason)
            self._send_response(APIResponse(
                success=success,
                data={'message': 'Optimization triggered' if success else 'Optimization failed'}
            ))
        elif self.scheduler:
            from adaptive.scheduler import SchedulePriority
            task = self.scheduler.schedule(
                strategy_name,
                reason,
                SchedulePriority.HIGH,
                force=True
            )
            self._send_response(APIResponse(
                success=task is not None,
                data={'task_id': task.id if task else None}
            ))
        else:
            self._send_response(APIResponse(
                success=False,
                error="No optimization system available",
                status_code=503
            ))

    def _handle_approve_deployment(self):
        """Approve a pending deployment."""
        body = self._get_json_body() or {}
        request_id = body.get('request_id')

        if not request_id or request_id not in self.approval_requests:
            self._send_response(APIResponse(
                success=False,
                error="Invalid request_id",
                status_code=400
            ))
            return

        # Mark as approved
        self.approval_requests[request_id]['approved'] = True
        self.approval_requests[request_id]['approved_at'] = datetime.now().isoformat()

        self._send_response(APIResponse(
            success=True,
            data={'message': 'Deployment approved'}
        ))

    def _handle_reject_deployment(self):
        """Reject a pending deployment."""
        body = self._get_json_body() or {}
        request_id = body.get('request_id')
        reason = body.get('reason', 'Rejected by agent')

        if not request_id or request_id not in self.approval_requests:
            self._send_response(APIResponse(
                success=False,
                error="Invalid request_id",
                status_code=400
            ))
            return

        # Mark as rejected
        self.approval_requests[request_id]['approved'] = False
        self.approval_requests[request_id]['rejected_at'] = datetime.now().isoformat()
        self.approval_requests[request_id]['rejection_reason'] = reason

        self._send_response(APIResponse(
            success=True,
            data={'message': 'Deployment rejected'}
        ))

    def _handle_rollback(self):
        """Trigger a rollback."""
        body = self._get_json_body() or {}
        strategy_name = body.get('strategy_name')
        to_version = body.get('to_version')

        if not strategy_name:
            self._send_response(APIResponse(
                success=False,
                error="strategy_name required",
                status_code=400
            ))
            return

        if not self.adaptive_optimizer:
            self._send_response(APIResponse(
                success=False,
                error="Rollback not available: no adaptive optimizer attached to API server",
                status_code=501
            ))
            return

        success = self.adaptive_optimizer.deployer.rollback(strategy_name, to_version)
        if success:
            self._send_response(APIResponse(
                success=True,
                data={'message': f'Rolled back {strategy_name}'
                                 + (f' to {to_version}' if to_version else ' to previous version')}
            ))
        else:
            self._send_response(APIResponse(
                success=False,
                error=f"Rollback failed for {strategy_name}, check server logs",
                status_code=500
            ))


class AgentAPI:
    """
    Main API server class.

    Usage:
        api = AgentAPI(
            host='0.0.0.0',
            port=8090,
            api_key='your-secret-key'
        )
        api.start()
    """

    def __init__(
        self,
        host: str = '0.0.0.0',
        port: int = 8090,
        api_key: Optional[str] = None,
        performance_db: Optional[PerformanceDB] = None,
        version_control: Optional[StrategyVersionControl] = None,
        adaptive_optimizer: Optional[AdaptiveOptimizer] = None,
        scheduler: Optional[OptimizationScheduler] = None,
    ):
        """
        Initialize API server.

        Args:
            host: Host to bind to
            port: Port to listen on
            api_key: Master API key
            performance_db: Performance database
            version_control: Version control system
            adaptive_optimizer: Adaptive optimizer
            scheduler: Optimization scheduler
        """
        self.host = host
        self.port = port

        # Set up authentication
        self.auth_manager = AuthManager(master_key=api_key)

        # Set class-level references for handler
        AgentAPIHandler.auth_manager = self.auth_manager
        AgentAPIHandler.performance_db = performance_db
        AgentAPIHandler.version_control = version_control
        AgentAPIHandler.adaptive_optimizer = adaptive_optimizer
        AgentAPIHandler.scheduler = scheduler

        self._server: Optional[HTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the API server in a background thread."""
        self._server = HTTPServer((self.host, self.port), AgentAPIHandler)

        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True
        )
        self._server_thread.start()

        logger.info(f"Agent API server started on {self.host}:{self.port}")

    def stop(self) -> None:
        """Stop the API server."""
        if self._server:
            self._server.shutdown()
            self._server = None

        logger.info("Agent API server stopped")

    def add_approval_request(
        self,
        request_id: str,
        strategy_name: str,
        version_id: str,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Add a deployment approval request.

        Args:
            request_id: Unique request ID
            strategy_name: Strategy being deployed
            version_id: Version being deployed
            metrics: Backtest/shadow metrics
        """
        AgentAPIHandler.approval_requests[request_id] = {
            'request_id': request_id,
            'strategy_name': strategy_name,
            'version_id': version_id,
            'metrics': metrics,
            'created_at': datetime.now().isoformat(),
            'approved': None,
        }

    def check_approval(self, request_id: str) -> Optional[bool]:
        """
        Check if a deployment was approved.

        Args:
            request_id: Request ID to check

        Returns:
            True if approved, False if rejected, None if pending
        """
        if request_id not in AgentAPIHandler.approval_requests:
            return None

        return AgentAPIHandler.approval_requests[request_id].get('approved')


def create_app(
    api_key: Optional[str] = None,
    **kwargs
) -> AgentAPI:
    """
    Factory function to create API server.

    Args:
        api_key: Master API key
        **kwargs: Additional arguments for AgentAPI

    Returns:
        AgentAPI instance
    """
    return AgentAPI(api_key=api_key, **kwargs)
