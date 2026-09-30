class NotifierError(Exception):
    pass


class NotifierClient:
    """Pretend real external client. In this fixture it is deterministic and
    local so tests are hermetic, but it is NOT the stub notifier.py is meant
    to stop bypassing: it fails when the message is empty, exactly like a
    real HTTP client would fail on a malformed request."""

    def send(self, user_id, message):
        if not message:
            raise NotifierError("empty message rejected by notification service")
        return {"delivered_to": user_id, "message": message}
