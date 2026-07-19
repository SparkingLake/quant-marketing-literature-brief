import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from main import Source, classify, make_paper, normalized_text, years_before  # noqa: E402

TOPICS = {
    "IO": {"title_anchors": ["market power"], "abstract_support": ["competition"]},
    "Quant": {"title_anchors": ["dynamic pricing"], "abstract_support": ["retail"]},
}


class ClassifierTests(unittest.TestCase):
    def test_title_anchor_is_required(self):
        score, labels, matches = classify("Retail competition", "We study dynamic pricing.", TOPICS)
        self.assertEqual((score, labels, matches), (0, (), ()))

    def test_title_anchor_has_high_score(self):
        score, labels, matches = classify("Dynamic Pricing with Retail Data", "", TOPICS)
        self.assertEqual(score, 50)
        self.assertEqual(labels, ("Quant",))
        self.assertEqual(matches, ("dynamic pricing",))

    def test_old_paper_is_rejected(self):
        record = {"DOI": "10.1000/example", "title": ["Dynamic Pricing"], "issued": {"date-parts": [[2018, 1, 1]]}}
        paper = make_paper(record, Source("Test", "Test", "/test"), TOPICS, date(2021, 7, 19))
        self.assertIsNone(paper)

    def test_leap_day_cutoff_is_valid(self):
        self.assertEqual(years_before(date(2028, 2, 29), 5), date(2023, 2, 28))

    def test_removes_html_from_metadata(self):
        self.assertEqual(normalized_text("<jats:title> A &amp; B </jats:title>"), "A & B")


if __name__ == "__main__":
    unittest.main()
