import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from main import classify, normalized_text  # noqa: E402


class ClassifierTests(unittest.TestCase):
    def test_classifies_platform_pricing_paper(self):
        topics = {"IO": ["market power", "platform"], "Quant": ["dynamic pricing"]}
        score, labels, matches = classify("Platform Market Power", "We study dynamic pricing.", topics)
        self.assertEqual(score, 42)
        self.assertEqual(labels, ("IO", "Quant"))
        self.assertIn("dynamic pricing", matches)

    def test_removes_html_from_metadata(self):
        self.assertEqual(normalized_text("<jats:title> A &amp; B </jats:title>"), "A & B")


if __name__ == "__main__":
    unittest.main()
