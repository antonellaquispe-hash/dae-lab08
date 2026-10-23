from rest_framework.permissions import BasePermission

AGENT_GROUP = "agente"


class AgentPermission(BasePermission):
    """Who may do what. This is the SERVER's rule: it holds even if a client misbehaves.

    The rule the lab asks for:
      - a person (user with is_staff) can do anything;
      - a member of the group «agente» can read, create and modify, but NEVER delete;
      - anybody else who is logged in can only read;
      - an unknown method is denied (deny by default).

    TODO(team): implement it. As it stands, `return True` lets everything through, so the
    agent's token can delete and `python manage.py test quiz.tests.test_permissions` fails.
    """

    def has_permission(self, request, view):
        return True  # TODO(team): replace this line with the rule above
