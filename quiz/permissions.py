from rest_framework.permissions import BasePermission

AGENT_GROUP = "agente"


class AgentPermission(BasePermission):
    """Who may do what. This is the SERVER's rule: it holds even if a client misbehaves.

    The rule the lab asks for:
      - a person (user with is_staff) can do anything;
      - a member of the group «agente» can read, create and modify, but NEVER delete;
      - anybody else who is logged in can only read;
      - an unknown method is denied (deny by default).
    """

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return False
        if request.user.is_staff:
            return True
        if request.method in ("POST", "PUT", "PATCH"):
            return request.user.groups.filter(name=AGENT_GROUP).exists()
        return False
