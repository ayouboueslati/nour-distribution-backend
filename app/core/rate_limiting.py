from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"]
)

# Specific limits
login_limits = ["5/minute"]
admin_limits = ["100/minute"]
public_limits = ["30/minute"]