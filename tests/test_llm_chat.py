import os
import unittest

from app import llm_chat


class LlmChatTest(unittest.TestCase):
    def test_offline_answer_when_key_missing(self):
        old_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            self.assertFalse(llm_chat.configured())
            self.assertIn("AI chat is not configured", llm_chat.offline_answer())
        finally:
            if old_key:
                os.environ["OPENAI_API_KEY"] = old_key

    def test_extract_text_from_responses_output(self):
        data = {
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Use /voice to check Sicada setup.",
                        }
                    ]
                }
            ]
        }
        self.assertEqual(llm_chat.extract_text(data), "Use /voice to check Sicada setup.")

    def test_system_prompt_is_domain_bound(self):
        self.assertIn("Sicada.ai", llm_chat.SYSTEM_PROMPT)
        self.assertIn("outside this scope", llm_chat.SYSTEM_PROMPT)
        self.assertIn("Never ask the user to paste API keys", llm_chat.SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
