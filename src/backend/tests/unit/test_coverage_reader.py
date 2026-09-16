import io
import zipfile

from app.analysis.coverage_reader import read_coverage_from_artifact_zip, read_coverage_percentage


def _zip_with(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


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


class TestReadCoverageFromArtifactZip:
    def test_reads_coverage_xml_from_inside_the_zip(self):
        zip_bytes = _zip_with(
            {"coverage.xml": '<?xml version="1.0"?><coverage line-rate="0.9"></coverage>'}
        )
        assert read_coverage_from_artifact_zip(zip_bytes) == 90.0

    def test_reads_lcov_info_when_no_coverage_xml_present(self):
        zip_bytes = _zip_with({"lcov.info": "LF:100\nLH:25\n"})
        assert read_coverage_from_artifact_zip(zip_bytes) == 25.0

    def test_finds_file_nested_in_a_subfolder(self):
        # O artifact do Jest, por exemplo, publica em "coverage/lcov.info".
        zip_bytes = _zip_with({"coverage/lcov.info": "LF:10\nLH:10\n"})
        assert read_coverage_from_artifact_zip(zip_bytes) == 100.0

    def test_returns_none_when_zip_has_no_relevant_file(self):
        zip_bytes = _zip_with({"README.md": "# nothing here"})
        assert read_coverage_from_artifact_zip(zip_bytes) is None

    def test_returns_none_for_corrupted_zip(self):
        assert read_coverage_from_artifact_zip(b"not a zip file") is None
