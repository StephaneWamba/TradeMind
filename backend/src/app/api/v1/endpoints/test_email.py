"""Test email endpoint."""

from fastapi import APIRouter
from app.services.notification.alerting import AlertingService

router = APIRouter()


@router.post("/test")
async def test_email():
    """Test email alerting service."""
    alerting_service = AlertingService()
    
    result = await alerting_service.send_alert(
        subject="Test Alert - TradeMind System",
        message="This is a test email to verify the email alerting service is working correctly.",
        priority="normal",
    )
    
    return {
        "success": result,
        "message": "Test email sent" if result else "Failed to send test email",
    }

