class SMCException(Exception):
    """Base exception for SMC Academy Referral application."""
    def __init__(self, message: str = "An unexpected error occurred."):
        self.message = message
        super().__init__(self.message)


class TelegramAuthError(SMCException):
    """Raised when Telegram initData validation fails or auth_date is expired."""
    pass


class InvalidTokenError(SMCException):
    """Raised when JWT authentication token is invalid or expired."""
    pass


class ReferralCodeNotFoundError(SMCException):
    """Raised when a referral code is not found or inactive."""
    pass


class WebhookAuthError(SMCException):
    """Raised when webhook secret validation fails."""
    pass


class DuplicateWebhookError(SMCException):
    """Raised when a Google Form response ID has already been processed."""
    pass
