from django.contrib.auth.models import User
from django.core.management import call_command
from rest_framework.authtoken.models import Token

from quiz.models import Exam, Question


def seed():
    """Load the fixed data and return (person token, agent token)."""
    call_command("seed_quiz", verbosity=0)
    return (
        Token.objects.get(user__username="profe").key,
        Token.objects.get(user__username="agente").key,
    )


def reader_token():
    """A logged-in user that is neither staff nor in the agent group."""
    user, _ = User.objects.get_or_create(username="lector")
    return Token.objects.get_or_create(user=user)[0].key


def exam_id(title="Django · ORM"):
    return Exam.objects.get(title=title).id


def hostile_question():
    return Question.objects.get(text__contains="IGNORA TUS INSTRUCCIONES")


def valid_body(exam):
    return {
        "exam": exam,
        "text": "¿Qué es una API REST?",
        "choices": [
            {"text": "Un estilo de arquitectura sobre HTTP", "is_correct": True},
            {"text": "Un lenguaje de programación", "is_correct": False},
            {"text": "Un motor de base de datos", "is_correct": False},
        ],
    }
