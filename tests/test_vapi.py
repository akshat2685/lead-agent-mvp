import unittest

from app.agent import final_provider_status, final_vapi_status
from app.sicada_adapter import normalize_phone as normalize_sicada_phone
from app.vapi_adapter import normalize_phone


class VapiAdapterTest(unittest.TestCase):
    def test_normalize_phone_requires_e164(self):
        self.assertEqual(normalize_phone("+1 (415) 555-0100"), "+14155550100")
        with self.assertRaises(ValueError):
            normalize_phone("415-555-0100")

    def test_sicada_normalize_phone_requires_e164(self):
        self.assertEqual(normalize_sicada_phone("+91 98765 43210"), "+919876543210")
        with self.assertRaises(ValueError):
            normalize_sicada_phone("9876543210")

    def test_final_vapi_status(self):
        self.assertEqual(final_vapi_status("assistant-ended-call", "hello", ""), "contacted")
        self.assertEqual(final_vapi_status("customer-did-not-answer", "", ""), "follow_up")
        self.assertEqual(final_vapi_status("busy", "short artifact", ""), "follow_up")

    def test_final_provider_status_handles_common_sicada_outcomes(self):
        self.assertEqual(final_provider_status("call.completed answered", "", "Interested lead"), "contacted")
        self.assertEqual(final_provider_status("call.no_answer", "", ""), "follow_up")
        self.assertEqual(final_provider_status("busy", "", ""), "follow_up")


if __name__ == "__main__":
    unittest.main()
