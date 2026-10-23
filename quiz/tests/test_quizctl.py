"""The client status handling and requests against an actual local HTTP server."""
import io
import json

from django.test import LiveServerTestCase, SimpleTestCase

import quizctl

from .helpers import exam_id, seed


class ExitCodeTests(SimpleTestCase):
    def test_success_is_zero(self):
        for status in (200, 201, 204):
            self.assertEqual(quizctl.exit_code_for(status), 0, status)

    def test_validation_is_two(self):
        self.assertEqual(quizctl.exit_code_for(400), 2)

    def test_not_allowed_is_three(self):
        self.assertEqual(quizctl.exit_code_for(401), 3)
        self.assertEqual(quizctl.exit_code_for(403), 3)

    def test_not_found_is_four(self):
        self.assertEqual(quizctl.exit_code_for(404), 4)

    def test_server_errors_are_five(self):
        self.assertEqual(quizctl.exit_code_for(500), 5)
        self.assertEqual(quizctl.exit_code_for(503), 5)

    def test_anything_else_is_one(self):
        for status in (302, 405, 409):
            self.assertEqual(quizctl.exit_code_for(status), 1, status)


class PayloadTests(SimpleTestCase):
    def test_ok_marks_the_correct_choice(self):
        body = quizctl.build_question_payload(3, "¿Qué es REST?", ["Un estilo:ok", "Un lenguaje"])
        self.assertEqual(body, {
            "exam": 3, "text": "¿Qué es REST?",
            "choices": [{"text": "Un estilo", "is_correct": True}, {"text": "Un lenguaje", "is_correct": False}],
        })

    def test_only_the_final_ok_counts(self):
        body = quizctl.build_question_payload(1, "t", ["Verdad: sí:ok", "ok es una palabra"])
        self.assertEqual(body["choices"][0], {"text": "Verdad: sí", "is_correct": True})
        self.assertEqual(body["choices"][1], {"text": "ok es una palabra", "is_correct": False})

    def test_it_does_not_validate_that_is_the_servers_job(self):
        body = quizctl.build_question_payload(1, "t", ["a:ok", "b:ok"])  # two correct: the server will say 400
        self.assertEqual(sum(c["is_correct"] for c in body["choices"]), 2)


class CliLiveTests(LiveServerTestCase):
    host = "127.0.0.1"  # not «localhost»: on Windows it tries IPv6 first and every request waits

    def setUp(self):
        self.person, self.agent = seed()
        self.env = {"QUIZ_URL": self.live_server_url, "QUIZ_TOKEN": self.person}

    def run_cli(self, *argv, env=None):
        out = io.StringIO()
        code = quizctl.main(list(argv), env=env or self.env, out=out)
        return code, out.getvalue()

    def test_exams_list(self):
        code, text = self.run_cli("exams", "list")
        self.assertEqual(code, 0)
        self.assertIn("Django · ORM", text)

    def test_json_output_is_stable(self):
        code, text = self.run_cli("--json", "questions", "list", "--exam", str(exam_id()))
        payload = json.loads(text)
        self.assertEqual((code, payload["status"]), (0, 200))
        self.assertEqual(payload["data"]["count"], 4)

    def test_create_a_valid_question(self):
        code, text = self.run_cli("--json", "questions", "create", "--exam", str(exam_id()), "--text", "¿Qué es REST?",
                                  "--choice", "Un estilo:ok", "--choice", "Un lenguaje")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)["status"], 201)

    def test_two_correct_choices_exit_two_with_the_reason(self):
        code, text = self.run_cli("questions", "create", "--exam", str(exam_id()), "--text", "t",
                                  "--choice", "a:ok", "--choice", "b:ok")
        self.assertEqual(code, 2)
        self.assertIn("exactamente una", text)

    def test_dry_run_describes_and_creates_nothing(self):
        code, text = self.run_cli("--dry-run", "questions", "create", "--exam", str(exam_id()), "--text", "t",
                                  "--choice", "a:ok", "--choice", "b")
        self.assertEqual(code, 0)
        self.assertIn("[dry-run] POST", text)
        _, listing = self.run_cli("--json", "questions", "list")
        self.assertEqual(json.loads(listing)["data"]["count"], 8)

    def test_a_missing_question_exits_four(self):
        self.assertEqual(self.run_cli("questions", "get", "99999")[0], 4)

    def test_the_agent_token_cannot_delete_exit_three(self):
        """Needs part 3 done: the SERVER must answer 403 to the agent's DELETE."""
        env = {**self.env, "QUIZ_TOKEN": self.agent}
        first = json.loads(self.run_cli("--json", "questions", "list", env=env)[1])["data"]["results"][0]["id"]
        self.assertEqual(self.run_cli("questions", "delete", str(first), env=env)[0], 3)

    def test_a_wrong_token_exits_three(self):
        env = {**self.env, "QUIZ_TOKEN": "nonsense"}
        self.assertEqual(self.run_cli("exams", "list", env=env)[0], 3)

    def test_no_token_is_a_usage_error(self):
        self.assertEqual(self.run_cli("exams", "list", env={"QUIZ_URL": self.live_server_url})[0], 1)

    def test_no_connection_exits_six(self):
        self.assertEqual(self.run_cli("exams", "list", env={"QUIZ_URL": "http://127.0.0.1:9", "QUIZ_TOKEN": "x"})[0], 6)

    def test_ops_lists_the_contract(self):
        code, text = self.run_cli("ops")
        self.assertEqual(code, 0)
        self.assertIn("questions_destroy", text)
