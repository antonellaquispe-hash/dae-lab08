"""The API itself (the one the official Lab 8 builds) and its contract. All of this passes as delivered."""
import requests

from django.test import LiveServerTestCase
from rest_framework.test import APITestCase

from agent.gateway import ALLOWED
from quiz.models import Choice, Exam, Question

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

    def test_exams_support_create_retrieve_update_and_delete(self):
        created = self.client.post("/api/exams/", {"title": "HTTP"}, format="json")
        self.assertEqual(created.status_code, 201)
        exam_url = f"/api/exams/{created.json()['id']}/"
        self.assertEqual(self.client.get(exam_url).status_code, 200)
        self.assertEqual(self.client.put(exam_url, {"title": "HTTP actualizado"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(exam_url, {"title": "HTTP parcial"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(exam_url).status_code, 204)
        self.assertEqual(self.client.get(exam_url).status_code, 404)

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

    def test_put_replaces_a_question_and_its_nested_choices(self):
        question = Question.objects.first()
        response = self.client.put(
            f"/api/questions/{question.id}/", valid_body(question.exam_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["choices"]), 3)

    def test_choice_resource_can_be_listed_created_retrieved_updated_and_deleted(self):
        question = Question.objects.first()
        self.assertEqual(self.client.get("/api/choices/").status_code, 200)
        created = self.client.post(
            "/api/choices/", {"question": question.id, "text": "Otra opción", "is_correct": False},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        choice_url = f"/api/choices/{created.json()['id']}/"
        self.assertEqual(self.client.get(choice_url).status_code, 200)
        replaced = self.client.put(
            choice_url,
            {"question": question.id, "text": "Opción reemplazada", "is_correct": False},
            format="json",
        )
        self.assertEqual(replaced.status_code, 200)
        updated = self.client.patch(choice_url, {"text": "Opción actualizada"}, format="json")
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(self.client.delete(choice_url).status_code, 204)

    def test_choice_resource_preserves_the_question_correct_answer_invariant(self):
        question = Question.objects.first()
        response = self.client.post(
            "/api/choices/", {"question": question.id, "text": "Otra correcta", "is_correct": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        correct = question.choices.get(is_correct=True)
        response = self.client.delete(f"/api/choices/{correct.id}/")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Choice.objects.filter(pk=correct.id).exists())

    def test_a_person_can_delete_and_then_it_is_gone(self):
        question = Question.objects.first()
        self.assertEqual(self.client.delete(f"/api/questions/{question.id}/").status_code, 204)
        self.assertEqual(self.client.get(f"/api/questions/{question.id}/").status_code, 404)


class ExternalHttpTests(LiveServerTestCase):
    """Exercise router operations through requests against an actual HTTP server."""
    host = "127.0.0.1"

    def setUp(self):
        self.person, _ = seed()
        self.headers = {"Authorization": f"Token {self.person}", "Accept": "application/json"}

    def request(self, method, path, **kwargs):
        return requests.request(
            method, self.live_server_url + path, headers=self.headers, timeout=10, **kwargs
        )

    def test_crud_operations_and_validation_statuses_over_http(self):
        exams = self.request("GET", "/api/exams/")
        self.assertEqual(exams.status_code, 200)
        exam_id_value = exams.json()["results"][0]["id"]

        created_exam = self.request("POST", "/api/exams/", json={"title": "HTTP externo"})
        self.assertEqual(created_exam.status_code, 201)
        exam_url = f"/api/exams/{created_exam.json()['id']}/"
        self.assertEqual(self.request("GET", exam_url).status_code, 200)
        self.assertEqual(self.request("PUT", exam_url, json={"title": "HTTP completo"}).status_code, 200)
        self.assertEqual(self.request("PATCH", exam_url, json={"title": "HTTP parcial"}).status_code, 200)
        self.assertEqual(self.request("DELETE", exam_url).status_code, 204)

        body = valid_body(exam_id_value)
        created_question = self.request("POST", "/api/questions/", json=body)
        self.assertEqual(created_question.status_code, 201)
        question_id = created_question.json()["id"]
        question_url = f"/api/questions/{question_id}/"
        self.assertEqual(self.request("GET", question_url).status_code, 200)
        self.assertEqual(self.request("PUT", question_url, json=body).status_code, 200)
        self.assertEqual(self.request("PATCH", question_url, json={"text": "Actualizada por HTTP"}).status_code, 200)

        choices = self.request("GET", "/api/choices/")
        self.assertEqual(choices.status_code, 200)
        choice = choices.json()["results"][0]
        choice_url = f"/api/choices/{choice['id']}/"
        self.assertEqual(self.request("GET", choice_url).status_code, 200)
        extra_choice = self.request(
            "POST", "/api/choices/", json={"question": question_id, "text": "Extra", "is_correct": False}
        )
        self.assertEqual(extra_choice.status_code, 201)
        extra_url = f"/api/choices/{extra_choice.json()['id']}/"
        replaced_choice = self.request(
            "PUT", extra_url,
            json={"question": question_id, "text": "Extra reemplazada", "is_correct": False},
        )
        self.assertEqual(replaced_choice.status_code, 200)
        self.assertEqual(self.request("PATCH", extra_url, json={"text": "Extra actualizada"}).status_code, 200)
        self.assertEqual(self.request("DELETE", extra_url).status_code, 204)

        missing = self.request("POST", "/api/questions/", json={"exam": exam_id_value, "choices": []})
        self.assertEqual(missing.status_code, 400)
        wrong_type = self.request("POST", "/api/questions/", json={**body, "exam": "incorrecto"})
        self.assertEqual(wrong_type.status_code, 400)
        wrong_answer_count = {**body, "choices": [dict(c, is_correct=True) for c in body["choices"]]}
        invalid_answer = self.request("POST", "/api/questions/", json=wrong_answer_count)
        self.assertEqual(invalid_answer.status_code, 400)

        self.assertEqual(self.request("DELETE", question_url).status_code, 204)
        self.assertEqual(self.request("GET", question_url).status_code, 404)

class ContractTests(APITestCase):
    def test_swagger_docs_page_renders(self):
        self.assertEqual(self.client.get("/api/docs/").status_code, 200)

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

