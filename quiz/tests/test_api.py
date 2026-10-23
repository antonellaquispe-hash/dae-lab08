"""The API itself (the one the official Lab 8 builds) and its contract. All of this passes as delivered."""
from rest_framework.test import APITestCase

from agent.gateway import ALLOWED
from quiz.models import Question

from .helpers import exam_id, seed, valid_body


class ApiTests(APITestCase):
    def setUp(self):
        self.person, self.agent = seed()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.person}")

    def test_no_token_is_401(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/exams/").status_code, 401)

    def test_a_wrong_token_is_401(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token nonsense")
        self.assertEqual(self.client.get("/api/exams/").status_code, 401)

    def test_exams_are_listed_with_their_question_count(self):
        data = self.client.get("/api/exams/").json()
        self.assertEqual(data["count"], 2)
        self.assertEqual({e["question_count"] for e in data["results"]}, {4})

    def test_questions_are_paginated_five_at_a_time(self):
        data = self.client.get("/api/questions/").json()
        self.assertEqual((data["count"], len(data["results"])), (8, 5))
        self.assertIsNotNone(data["next"])

    def test_questions_can_be_filtered_by_exam(self):
        data = self.client.get("/api/questions/", {"exam": exam_id("Django · Plantillas")}).json()
        self.assertEqual(data["count"], 4)

    def test_questions_can_be_searched_by_text(self):
        data = self.client.get("/api/questions/", {"search": "prefetch_related"}).json()
        self.assertEqual(data["count"], 1)

    def test_choices_travel_nested_inside_the_question(self):
        first = self.client.get("/api/questions/").json()["results"][0]
        self.assertEqual(len(first["choices"]), 4)
        self.assertEqual(sum(c["is_correct"] for c in first["choices"]), 1)

    def test_a_valid_question_is_created_with_201(self):
        response = self.client.post("/api/questions/", valid_body(exam_id()), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.json()["choices"]), 3)
        self.assertEqual(Question.objects.count(), 9)

    def test_two_correct_choices_is_400_and_saves_nothing(self):
        body = valid_body(exam_id())
        body["choices"][1]["is_correct"] = True
        response = self.client.post("/api/questions/", body, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("exactamente una", str(response.json()))
        self.assertEqual(Question.objects.count(), 8)

    def test_a_missing_required_field_is_400(self):
        body = valid_body(exam_id())
        del body["text"]
        self.assertEqual(self.client.post("/api/questions/", body, format="json").status_code, 400)

    def test_a_wrong_type_is_400(self):
        body = valid_body(exam_id())
        body["exam"] = "no-es-un-numero"
        self.assertEqual(self.client.post("/api/questions/", body, format="json").status_code, 400)

    def test_patch_changes_only_what_is_sent(self):
        question = Question.objects.first()
        response = self.client.patch(f"/api/questions/{question.id}/", {"text": "Nuevo enunciado"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["choices"]), 4)

    def test_a_person_can_delete_and_then_it_is_gone(self):
        question = Question.objects.first()
        self.assertEqual(self.client.delete(f"/api/questions/{question.id}/").status_code, 204)
        self.assertEqual(self.client.get(f"/api/questions/{question.id}/").status_code, 404)


class ContractTests(APITestCase):
    def test_every_operation_the_gateway_offers_exists_in_the_contract(self):
        """If the API changes and the allowlist does not, this fails: the contract is the source of truth."""
        seed()
        schema = self.client.get("/api/schema/", {"format": "json"}).json()
        declared = {
            op["operationId"]
            for methods in schema["paths"].values()
            for method, op in methods.items()
            if method in ("get", "post", "put", "patch", "delete")
        }
        self.assertEqual(set(ALLOWED) - declared, set())

    def test_the_contract_declares_token_authentication(self):
        schema = self.client.get("/api/schema/", {"format": "json"}).json()
        self.assertIn("tokenAuth", schema["components"]["securitySchemes"])
