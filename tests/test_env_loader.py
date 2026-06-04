import os
import tempfile
import unittest
from pathlib import Path

from app.env_loader import load_env


class EnvLoaderTest(unittest.TestCase):
    def test_load_env_without_overriding_existing_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / ".env"
            path.write_text(
                "\n".join(
                    [
                        "NEW_VALUE=loaded",
                        "QUOTED_VALUE='quoted text'",
                        "EXISTING_VALUE=from-file",
                        "# COMMENTED=ignored",
                    ]
                )
            )
            os.environ["EXISTING_VALUE"] = "from-os"
            try:
                loaded = load_env(path)
                self.assertEqual(loaded, 2)
                self.assertEqual(os.environ["NEW_VALUE"], "loaded")
                self.assertEqual(os.environ["QUOTED_VALUE"], "quoted text")
                self.assertEqual(os.environ["EXISTING_VALUE"], "from-os")
            finally:
                for key in ("NEW_VALUE", "QUOTED_VALUE", "EXISTING_VALUE"):
                    os.environ.pop(key, None)


if __name__ == "__main__":
    unittest.main()
