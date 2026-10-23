"""Part 4 of the lab: the agent's boundary. What the gateway lets through and what it stops.

All of this passes as delivered. The tests run against a real server started by the test, so the
gateway talks HTTP exactly as it would in the lab.
"""
import json
import os
import tempfile
from unittest import mock

from django.test import LiveServerTestCase, SimpleTestCase

from agent import gateway, llm
from quiz.models import Exam, Question

from .helpers import exam_id, hostile_question, seed


class GatewayTests(LiveServerTestCase):
    host = "127.0.0.1"  # not «localhost»: on Windows it tries IPv6 first and every request waits

    def setUp(self):
        self.person, self.agent = seed()
        self.audit = os.path.join(tempfile.mkdtemp(), "audit.jsonl")

    def run_intent(self, intent, **kwargs):
        return gateway.execute(intent, base_url=self.live_server_url, agent_token=self.agent,
                               audit_path=self.audit, **kwargs)

    # --- what it lets through -------------------------------------------------------------

    def test_a_read_runs_and_comes_back_marked_untrusted(self):
        result = self.run_intent({"op": "exams_list"})
        self.assertEqual((result["status"], result["http"]), ("ok", 200))
        self.assertEqual(result["untrusted_data"]["count"], 2)

    def test_the_hostile_text_is_data_not_an_order(self):
        result = self.run_intent({"op": "questions_list", "query": {"search": "IGNORA"}})
        texts = [q["text"] for q in result["untrusted_data"]["results"]]
        self.assertTrue(any("IGNORA TUS INSTRUCCIONES" in t for t in texts))  # present, but only as data
        self.assertEqual(Exam.objects.count(), 2)  # and nothing was deleted

    def test_a_model_that_obeys_the_hostile_text_only_gets_a_plan(self):
        intent = {"op": "exams_destroy", "path": {"id": exam_id()}}  # what the hostile text asks for
        result = self.run_intent(intent)
        self.assertEqual(result["status"], "approval_required")
        self.assertEqual(result["plan"]["target"]["title"], "Django · ORM")
        self.assertEqual(Exam.objects.count(), 2)

    def test_the_agent_can_create_a_question(self):
        body = {"exam": exam_id(), "text": "¿Qué es REST?",
                "choices": [{"text": "Un estilo", "is_correct": True}, {"text": "Un lenguaje", "is_correct": False}]}
        result = self.run_intent({"op": "questions_create", "body": body})
        self.assertEqual((result["status"], result["http"]), ("ok", 201))

    def test_the_server_validates_the_body_the_gateway_forwards(self):
        body = {"exam": exam_id(), "text": "t",
                "choices": [{"text": "a", "is_correct": True}, {"text": "b", "is_correct": True}]}
        result = self.run_intent({"op": "questions_create", "body": body})
        self.assertEqual((result["status"], result["http"]), ("error", 400))

    # --- the approval of a destructive plan ------------------------------------------------

    def test_a_person_approving_the_exact_plan_applies_it_with_their_own_token(self):
        question = hostile_question()
        intent = {"op": "questions_destroy", "path": {"id": question.id}}
        digest = self.run_intent(intent)["plan"]["plan_hash"]
        result = self.run_intent(intent, approval=digest, human_token=self.person)
        self.assertEqual((result["status"], result["http"]), ("applied", 204))
        self.assertFalse(Question.objects.filter(id=question.id).exists())

    def test_the_approval_without_the_persons_token_is_denied(self):
        question = hostile_question()
        intent = {"op": "questions_destroy", "path": {"id": question.id}}
        digest = self.run_intent(intent)["plan"]["plan_hash"]
        result = self.run_intent(intent, approval=digest)  # the agent alone cannot finish it
        self.assertEqual(result["status"], "denied")
        self.assertTrue(Question.objects.filter(id=question.id).exists())

    def test_the_approval_dies_if_the_data_changed_after_the_person_looked(self):
        target = exam_id()
        intent = {"op": "exams_destroy", "path": {"id": target}}
        digest = self.run_intent(intent)["plan"]["plan_hash"]
        Question.objects.create(exam_id=target, text="Llegó tarde")  # the exam now has one more question
        result = self.run_intent(intent, approval=digest, human_token=self.person)
        self.assertEqual(result["status"], "approval_required")
        self.assertTrue(Exam.objects.filter(id=target).exists())

    def test_an_approval_for_another_plan_is_worthless(self):
        intent = {"op": "exams_destroy", "path": {"id": exam_id()}}
        result = self.run_intent(intent, approval="000000000000", human_token=self.person)
        self.assertEqual(result["status"], "approval_required")

    def test_deleting_something_that_does_not_exist_is_not_found(self):
        self.assertEqual(self.run_intent({"op": "questions_destroy", "path": {"id": 99999}})["status"], "not_found")

    # --- what it stops ----------------------------------------------------------------------

    def test_code_is_not_an_intent(self):
        self.assertEqual(self.run_intent("Exam.objects.all().delete()")["status"], "denied")

    def test_unknown_operations_are_denied(self):
        for op in ("eval", "run_sql", "users_list", "exams_update", "exams_partial_update"):
            self.assertEqual(self.run_intent({"op": op})["status"], "denied", op)

    def test_arguments_must_fit_exactly(self):
        bad = [
            {"op": "questions_retrieve"},                                          # missing the id
            {"op": "questions_retrieve", "path": {"id": "1"}},                      # a string
            {"op": "questions_retrieve", "path": {"id": True}},                     # a bool is not an id
            {"op": "questions_retrieve", "path": {"id": 1, "extra": 1}},            # extra key
            {"op": "questions_list", "query": {"secret": "x"}},                     # unknown parameter
            {"op": "questions_list", "query": {"exam": "uno"}},                     # wrong type
            {"op": "exams_list", "body": {"x": 1}},                                 # a read with a body
            {"op": "questions_create", "body": {"text": "t"}},                      # incomplete body
            {"op": "exams_list", "token": "robado"},                                # unknown key in the intent
        ]
        for intent in bad:
            self.assertEqual(self.run_intent(intent)["status"], "denied", intent)

    def test_an_operation_that_left_the_contract_is_no_longer_offered(self):
        with mock.patch.dict(gateway.ALLOWED, {"exams_update_secret": "R0"}):
            result = self.run_intent({"op": "exams_update_secret"})
        self.assertEqual(result["status"], "denied")
        self.assertIn("contrato", result["reason"])

    # --- the trail --------------------------------------------------------------------------

    def test_every_decision_leaves_a_line_in_the_audit_log(self):
        self.run_intent({"op": "exams_list"})
        self.run_intent({"op": "eval"})
        self.run_intent({"op": "exams_destroy", "path": {"id": exam_id()}})
        lines = [json.loads(line) for line in open(self.audit, encoding="utf-8")]
        self.assertEqual([(x["op"], x["outcome"]) for x in lines],
                         [("exams_list", "ok"), ("eval", "denied"), ("exams_destroy", "approval_required")])
        self.assertTrue(all(x["actor"] == "agent" for x in lines))


class ModelAdapterTests(SimpleTestCase):
    def test_it_parses_an_intent_wrapped_in_fences(self):
        reply = 'Claro:\n```json\n{"op": "exams_list"}\n```'
        self.assertEqual(llm.parse_intent(reply), {"op": "exams_list"})

    def test_a_reply_without_json_is_an_error(self):
        with self.assertRaises(ValueError):
            llm.parse_intent("No puedo ayudarte con eso.")

    def test_ask_model_uses_the_endpoint_and_lists_the_closed_operations(self):
        sent = {}

        def fake_post(url, payload):
            sent["url"], sent["payload"] = url, payload
            return {"choices": [{"message": {"content": '{"op": "exams_list"}'}}]}

        with mock.patch.dict(os.environ, {"LLM_URL": "http://llm.local/v1/"}):
            intent = llm.ask_model("¿cuántos exámenes hay?", post=fake_post)
        self.assertEqual(intent, {"op": "exams_list"})
        self.assertEqual(sent["url"], "http://llm.local/v1/chat/completions")
        system = sent["payload"]["messages"][0]["content"]
        self.assertIn("questions_destroy [R2]", system)
        self.assertNotIn("Token", system)  # the model is never given a credential
