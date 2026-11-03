import logging


class RedactingFilter(logging.Filter):
    """Belt-and-suspenders redaction: the app should never log secrets in
    the first place, but this strips known secret substrings from any log
    record that slips through, so a bug elsewhere doesn't leak a key."""

    def __init__(self, secrets: list[str]):
        super().__init__()
        self._secrets = [s for s in secrets if s]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for secret in self._secrets:
            if secret in message:
                message = message.replace(secret, "[REDACTED]")
        record.msg = message
        record.args = ()
        return True


def configure_logging(app) -> None:
    secrets = [app.config.get("SECRET_KEY", ""), app.config.get("ANTHROPIC_API_KEY", "")]
    handler = logging.StreamHandler()
    handler.addFilter(RedactingFilter(secrets))
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO if not app.debug else logging.DEBUG)
