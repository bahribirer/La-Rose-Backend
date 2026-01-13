from twilio.rest import Client
from app.core.config import settings

twilio_client = Client(
    settings.TWILIO_ACCOUNT_SID,
    settings.TWILIO_AUTH_TOKEN,
)

TWILIO_VERIFY_SID = settings.TWILIO_VERIFY_SID
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"  # sandbox

