"""Alerting service for critical trading events using Resend email."""

import structlog
from typing import Optional
from datetime import datetime, timezone

from app.core.config import settings

logger = structlog.get_logger(__name__)


class AlertingService:
    """Service for sending alerts via Resend email."""

    def __init__(self):
        self.resend_api_key = getattr(settings, "RESEND_API_KEY", None)
        self.default_receiver = getattr(
            settings, "ALERT_EMAIL_RECEIVER", "wambstephane@gmail.com")
        self.default_sender = getattr(
            settings, "ALERT_EMAIL_SENDER", "onboarding@resend.dev")
        self.enabled = self.resend_api_key is not None

        if not self.enabled:
            logger.warning(
                "Resend API key not configured - email alerts disabled")

    async def send_alert(
        self,
        subject: str,
        message: str,
        priority: str = "normal",
        receiver: Optional[str] = None,
    ) -> bool:
        """
        Send email alert via Resend.

        Args:
            subject: Email subject
            message: Email body (HTML supported)
            priority: Alert priority (normal, high, critical)
            receiver: Email receiver (defaults to configured receiver)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Email alerts disabled, skipping", subject=subject)
            return False

        receiver = receiver or self.default_receiver

        try:
            import httpx

            priority_emoji = {
                "normal": "ℹ️",
                "high": "⚠️",
                "critical": "🚨"
            }.get(priority, "ℹ️")

            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: {'#dc3545' if priority == 'critical' else '#ffc107' if priority == 'high' else '#17a2b8'};">
                        {priority_emoji} {subject}
                    </h2>
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        {message.replace(chr(10), '<br>')}
                    </div>
                    <p style="color: #6c757d; font-size: 12px; margin-top: 20px;">
                        Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}<br>
                        Priority: {priority.upper()}
                    </p>
                </div>
            </body>
            </html>
            """

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {self.resend_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": self.default_sender,
                        "to": [receiver],
                        "subject": f"{priority_emoji} {subject}",
                        "html": html_body,
                    },
                )

                if response.status_code == 200:
                    logger.info(
                        "Alert email sent",
                        subject=subject,
                        receiver=receiver,
                        priority=priority,
                    )
                    return True
                else:
                    logger.error(
                        "Failed to send alert email",
                        subject=subject,
                        status_code=response.status_code,
                        response=response.text,
                    )
                    return False

        except Exception as e:
            logger.error("Error sending alert email",
                         subject=subject, error=str(e))
            return False

    async def alert_daily_loss_limit(
        self, strategy_id: int, current_loss: float, limit: float
    ):
        """Send alert when daily loss limit is reached."""
        await self.send_alert(
            subject=f"Daily Loss Limit Reached - Strategy {strategy_id}",
            message=f"""
            <h3>Daily Loss Limit Alert</h3>
            <p><strong>Strategy ID:</strong> {strategy_id}</p>
            <p><strong>Current Loss:</strong> {current_loss:.2f}%</p>
            <p><strong>Limit:</strong> {limit:.2f}%</p>
            <p style="color: #dc3545;"><strong>Action:</strong> Trading has been paused for this strategy.</p>
            """,
            priority="critical",
        )

    async def alert_circuit_breaker(self, strategy_id: int, reason: str):
        """Send alert when circuit breaker is triggered."""
        await self.send_alert(
            subject=f"Circuit Breaker Triggered - Strategy {strategy_id}",
            message=f"""
            <h3>Circuit Breaker Alert</h3>
            <p><strong>Strategy ID:</strong> {strategy_id}</p>
            <p><strong>Reason:</strong> {reason}</p>
            <p style="color: #dc3545;"><strong>Action:</strong> Strategy has been paused.</p>
            """,
            priority="critical",
        )

    async def alert_portfolio_heat_limit(
        self, connection_id: int, current_heat: float, max_heat: float
    ):
        """Send alert when portfolio heat limit is exceeded."""
        await self.send_alert(
            subject=f"Portfolio Heat Limit Exceeded - Connection {connection_id}",
            message=f"""
            <h3>Portfolio Heat Alert</h3>
            <p><strong>Connection ID:</strong> {connection_id}</p>
            <p><strong>Current Heat:</strong> {current_heat:.2f}%</p>
            <p><strong>Max Heat:</strong> {max_heat:.2f}%</p>
            <p style="color: #ffc107;"><strong>Warning:</strong> Total portfolio risk is high. Consider reducing position sizes.</p>
            """,
            priority="high",
        )

    async def alert_order_failed(
        self, order_id: int, symbol: str, reason: str
    ):
        """Send alert when an order fails."""
        await self.send_alert(
            subject=f"Order Failed - {symbol}",
            message=f"""
            <h3>Order Failure Alert</h3>
            <p><strong>Order ID:</strong> {order_id}</p>
            <p><strong>Symbol:</strong> {symbol}</p>
            <p><strong>Reason:</strong> {reason}</p>
            """,
            priority="high",
        )

    async def alert_large_slippage(
        self, order_id: int, symbol: str, expected_price: float, actual_price: float, slippage_percent: float
    ):
        """Send alert when order experiences large slippage."""
        await self.send_alert(
            subject=f"Large Slippage Detected - {symbol}",
            message=f"""
            <h3>Slippage Alert</h3>
            <p><strong>Order ID:</strong> {order_id}</p>
            <p><strong>Symbol:</strong> {symbol}</p>
            <p><strong>Expected Price:</strong> ${expected_price:,.2f}</p>
            <p><strong>Actual Price:</strong> ${actual_price:,.2f}</p>
            <p><strong>Slippage:</strong> {slippage_percent:.2f}%</p>
            <p style="color: #ffc107;"><strong>Warning:</strong> Order executed with significant slippage.</p>
            """,
            priority="high",
        )

    async def alert_exchange_connection_failed(self, connection_id: int, error: str):
        """Send alert when exchange connection fails."""
        await self.send_alert(
            subject=f"Exchange Connection Failed - Connection {connection_id}",
            message=f"""
            <h3>Exchange Connection Alert</h3>
            <p><strong>Connection ID:</strong> {connection_id}</p>
            <p><strong>Error:</strong> {error}</p>
            <p style="color: #dc3545;"><strong>Action Required:</strong> Please check exchange API credentials and network connectivity.</p>
            """,
            priority="critical",
        )
