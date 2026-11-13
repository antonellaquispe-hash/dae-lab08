from django.test import SimpleTestCase, override_settings


@override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:5173"])
class CorsPolicyTests(SimpleTestCase):
    def test_allows_the_react_development_origin(self):
        response = self.client.options(
            "/api/exams/",
            HTTP_ORIGIN="http://localhost:5173",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
        )

        self.assertEqual(response["Access-Control-Allow-Origin"], "http://localhost:5173")
        self.assertIn("POST", response["Access-Control-Allow-Methods"])

    def test_rejects_other_localhost_ports_and_hosts(self):
        for origin in ("http://localhost:3000", "http://127.0.0.1:5173", "https://localhost:5173"):
            with self.subTest(origin=origin):
                response = self.client.get("/api/exams/", HTTP_ORIGIN=origin)
                self.assertNotIn("Access-Control-Allow-Origin", response)
