import unittest

from app.agent import final_vapi_status
from app.vapi_adapter import normalize_phone


class VapiAdapterTest(unittest.TestCase):
    def test_normalize_phone_requires_e164(self):
        self.assertEqual(normalize_phone("+1 (415) 555-0100"), "+14155550100")
        with self.assertRaises(ValueError):
            normalize_phone("415-555-0100")

    def test_final_vapi_status(self):
        self.assertEqual(final_vapi_status("assistant-ended-call", "hello", ""), "contacted")
        self.assertEqual(final_vapi_status("customer-did-not-answer", "", ""), "follow_up")
        self.assertEqual(final_vapi_status("busy", "short artifact", ""), "follow_up")


if __name__ == "__main__":
    unittest.main()
