"""
Email Service - Send invitation emails via Resend.
"""
import logging
import resend
from typing import Any, Dict

from app.config import settings

logger = logging.getLogger(__name__)


def _get_resend_client():
    if not settings.resend_api_key:
        raise ValueError("RESEND_API_KEY is not configured")
    resend.api_key = settings.resend_api_key


def send_invitation_email(
    to_email: str,
    inviter_name: str,
    workspace_name: str,
    invite_link: str,
) -> str:
    """Send a workspace invitation email and return provider email ID."""
    _get_resend_client()

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 520px; margin: 0 auto; padding: 32px 24px; color: #1a1a2e;">
      <h2 style="margin: 0 0 8px;">You've been invited to collaborate</h2>
      <p style="color: #555; margin: 0 0 24px; font-size: 15px;">
        <strong>{inviter_name}</strong> invited you to join the workspace
        <strong>&ldquo;{workspace_name}&rdquo;</strong> on Seagull.
      </p>
      <a href="{invite_link}"
         style="display: inline-block; background: #2563eb; color: #fff; padding: 12px 28px;
                border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 15px;">
        Accept Invitation
      </a>
      <p style="color: #888; font-size: 13px; margin-top: 28px;">
        This invitation expires in 7 days. If you didn't expect this, you can ignore this email.
      </p>
    </div>
    """

    try:
        params: resend.Emails.SendParams = {
            "from": "Seagull <onboarding@resend.dev>",
            "to": [to_email],
            "subject": f"{inviter_name} invited you to collaborate on Seagull",
            "html": html,
        }
        response = resend.Emails.send(params)
        provider_id = None
        if isinstance(response, dict):
            provider_id = response.get("id")
        else:
            provider_id = getattr(response, "id", None)
        if not provider_id:
            raise RuntimeError(f"Resend send response missing id: {response}")
        logger.info(f"Invitation email sent to {to_email}. provider_email_id={provider_id}")
        return provider_id
    except Exception as exc:
        logger.error(f"Failed to send invitation email to {to_email}: {exc}")
        raise RuntimeError(f"Failed to send invitation email: {exc}") from exc


def get_email_delivery_status(provider_email_id: str) -> Dict[str, Any]:
    """Fetch delivery status/events for a provider email id from Resend."""
    _get_resend_client()
    try:
        result = resend.Emails.get(provider_email_id)
        if isinstance(result, dict):
            data = result
        else:
            data = result.__dict__ if hasattr(result, "__dict__") else {"value": str(result)}
        return data
    except Exception as exc:
        logger.error(f"Failed to fetch email status for id={provider_email_id}: {exc}")
        raise RuntimeError(f"Failed to fetch email status: {exc}") from exc
