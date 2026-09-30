class AuthorizationError(Exception):
    pass


AUDIT_LOGS = [{"id": i, "event": f"event-{i}"} for i in range(1, 51)]


def list_pending_audits(current_user):
    """Only admins may list pending audit logs."""
    if not getattr(current_user, "is_admin", False):
        raise AuthorizationError("admin privileges required")
    return list(AUDIT_LOGS)
