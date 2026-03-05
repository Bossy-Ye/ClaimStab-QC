from __future__ import annotations

import unittest

from claimstab.results.report_sections import REPORT_SECTION_IDS, available_sections_text, is_section_enabled, parse_sections_arg


class TestReportSectionRegistry(unittest.TestCase):
    def test_available_sections_text_contains_known_ids(self) -> None:
        text = available_sections_text()
        for section_id in REPORT_SECTION_IDS:
            self.assertIn(section_id, text)

    def test_parse_sections_arg_empty_returns_none(self) -> None:
        self.assertIsNone(parse_sections_arg(""))
        self.assertIsNone(parse_sections_arg(" , "))

    def test_parse_sections_arg_returns_set(self) -> None:
        parsed = parse_sections_arg("summary,delta_sweep")
        self.assertEqual(parsed, {"summary", "delta_sweep"})

    def test_is_section_enabled(self) -> None:
        self.assertTrue(is_section_enabled("summary", None))
        self.assertTrue(is_section_enabled("summary", {"summary"}))
        self.assertFalse(is_section_enabled("summary", {"delta_sweep"}))


if __name__ == "__main__":
    unittest.main()
