"""Role tests: authorization is enforced by the server for every client."""
from rest_framework.test import APITestCase

from quiz.models import Choice, Question

from .helpers import exam_id, reader_token, seed, valid_body


class RoleTests(APITestCase):
    def setUp(self):
        self.person, self.agent = seed()
        self.reader = reader_token()

    def as_(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        return self.client

    def test_the_agent_can_read(self):
        self.assertEqual(self.as_(self.agent).get("/api/questions/").status_code, 200)

    def test_the_agent_can_create(self):
        response = self.as_(self.agent).post("/api/questions/", valid_body(exam_id()), format="json")
        self.assertEqual(response.status_code, 201)

    def test_the_agent_can_modify(self):
        question = Question.objects.first()
        response = self.as_(self.agent).patch(f"/api/questions/{question.id}/", {"text": "Otro"}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_the_agent_cannot_delete(self):
        question = Question.objects.first()
        response = self.as_(self.agent).delete(f"/api/questions/{question.id}/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Question.objects.filter(id=question.id).exists())

    def test_the_agent_cannot_delete_an_exam_either(self):
        self.assertEqual(self.as_(self.agent).delete(f"/api/exams/{exam_id()}/").status_code, 403)

    def test_the_agent_cannot_delete_a_choice(self):
        choice = Choice.objects.first()
        response = self.as_(self.agent).delete(f"/api/choices/{choice.id}/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Choice.objects.filter(id=choice.id).exists())

    def test_a_person_can_delete(self):
        question = Question.objects.first()
        self.assertEqual(self.as_(self.person).delete(f"/api/questions/{question.id}/").status_code, 204)

    def test_somebody_without_a_role_can_only_read(self):
        self.assertEqual(self.as_(self.reader).get("/api/questions/").status_code, 200)
        self.assertEqual(
            self.as_(self.reader).post("/api/questions/", valid_body(exam_id()), format="json").status_code, 403
        )

    def test_no_token_is_401_not_403(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/questions/").status_code, 401)
