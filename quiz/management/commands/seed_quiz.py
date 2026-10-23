from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from rest_framework.authtoken.models import Token

from quiz import seed_data
from quiz.models import Choice, Exam, Question
from quiz.permissions import AGENT_GROUP


def ensure_users():
    """The person (staff) and the agent (group «agente»), each with a token. Idempotent:
    running the seed again keeps the same tokens, so the environment variables stay valid."""
    group, _ = Group.objects.get_or_create(name=AGENT_GROUP)
    person, created = User.objects.get_or_create(username="profe", defaults={"is_staff": True})
    if created:
        person.set_unusable_password()
        person.save()
    agent, created = User.objects.get_or_create(username="agente")
    if created:
        agent.set_unusable_password()
        agent.save()
    agent.groups.add(group)
    return (
        Token.objects.get_or_create(user=person)[0].key,
        Token.objects.get_or_create(user=agent)[0].key,
    )


class Command(BaseCommand):
    help = "Carga los datos fijos del laboratorio y crea los usuarios «profe» y «agente» con su token."

    @transaction.atomic
    def handle(self, *args, **options):
        Exam.objects.all().delete()  # cascades to questions and choices
        for title, questions in seed_data.EXAMS:
            exam = Exam.objects.create(title=title)
            for text, choices in questions:
                question = Question.objects.create(exam=exam, text=text)
                Choice.objects.bulk_create(
                    Choice(question=question, text=t, is_correct=ok) for t, ok in choices
                )
        human, agent = ensure_users()

        if options["verbosity"] > 0:
            self.stdout.write(self.style.SUCCESS(
                f"Listo: {Exam.objects.count()} exámenes, {Question.objects.count()} preguntas."
            ))
            self.stdout.write("\nTokens (solo para esta máquina; el de la persona es el que puede borrar):")
            self.stdout.write("  PowerShell:")
            self.stdout.write(f'    $env:QUIZ_TOKEN_HUMANO = "{human}"')
            self.stdout.write(f'    $env:QUIZ_TOKEN_AGENTE = "{agent}"')
            self.stdout.write("  Bash:")
            self.stdout.write(f"    export QUIZ_TOKEN_HUMANO={human}")
            self.stdout.write(f"    export QUIZ_TOKEN_AGENTE={agent}")
