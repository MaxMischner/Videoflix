from django.test import TestCase


class LegalInformationEndpointTests(TestCase):
	def test_legal_overview_returns_links(self):
		response = self.client.get("/api/legal/")

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertEqual(payload["privacy"], "/api/legal/privacy/")
		self.assertEqual(payload["imprint"], "/api/legal/imprint/")

	def test_privacy_endpoint_returns_structured_content(self):
		response = self.client.get("/api/legal/privacy/")

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertIn("title", payload)
		self.assertIn("summary", payload)
		self.assertIn("sections", payload)
		self.assertTrue(payload["sections"])

	def test_imprint_endpoint_returns_structured_content(self):
		response = self.client.get("/api/legal/imprint/")

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertIn("title", payload)
		self.assertIn("summary", payload)
		self.assertIn("sections", payload)
		self.assertTrue(payload["sections"])
