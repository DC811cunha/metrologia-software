from app.analysis.coverage_reader import read_coverage_percentage


class TestReadCoveragePercentage:
    def test_reads_coverage_xml_line_rate(self, tmp_path):
        (tmp_path / "coverage.xml").write_text(
            '<?xml version="1.0"?><coverage line-rate="0.875"></coverage>',
            encoding="utf-8",
        )

        assert read_coverage_percentage(tmp_path) == 87.5

    def test_reads_lcov_info(self, tmp_path):
        (tmp_path / "lcov.info").write_text(
            "\n".join(
                [
                    "SF:src/a.js",
                    "LF:100",
                    "LH:80",
                    "end_of_record",
                    "SF:src/b.js",
                    "LF:50",
                    "LH:40",
                    "end_of_record",
                ]
            ),
            encoding="utf-8",
        )

        # (80 + 40) / (100 + 50) * 100
        assert read_coverage_percentage(tmp_path) == 80.0

    def test_reads_shields_io_style_badge_from_readme(self, tmp_path):
        (tmp_path / "README.md").write_text(
            "# Project\n\n![coverage](https://img.shields.io/badge/coverage-92%25-brightgreen)\n",
            encoding="utf-8",
        )

        assert read_coverage_percentage(tmp_path) == 92.0

    def test_prefers_coverage_xml_over_lcov_and_badge(self, tmp_path):
        (tmp_path / "coverage.xml").write_text(
            '<?xml version="1.0"?><coverage line-rate="0.5"></coverage>',
            encoding="utf-8",
        )
        (tmp_path / "lcov.info").write_text("LF:100\nLH:100\n", encoding="utf-8")

        assert read_coverage_percentage(tmp_path) == 50.0

    def test_returns_none_when_no_artifact_found(self, tmp_path):
        assert read_coverage_percentage(tmp_path) is None
