"""Suporte a monorepo: artifacts de cobertura do mesmo run de CI combinados e `extends` do tsconfig."""

import io
import zipfile
from pathlib import Path

import httpx

from app.analysis import coupling
from app.analysis.coverage_reader import read_coverage_from_artifact_zips
from app.core.config import settings
from app.services.github_service import GithubService

XML_BACKEND = '<?xml version="1.0"?><coverage line-rate="0.90" lines-valid="1000" lines-covered="900"></coverage>'


def zip_with(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def client_with(handler) -> httpx.Client:
    return httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(handler))


def artifact(artifact_id: int, name: str, run: int | None, expired: bool = False) -> dict:
    data: dict = {"id": artifact_id, "name": name, "expired": expired}
    if run is not None:
        data["workflow_run"] = {"id": run}
    return data


class TestCoverageArtifactsOfTheSameRun:
    def service(self, artifacts: list[dict], payloads: dict[int, bytes], requested: list[int]) -> GithubService:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/actions/artifacts"):
                return httpx.Response(200, json={"artifacts": artifacts})
            artifact_id = int(request.url.path.split("/")[-2])
            requested.append(artifact_id)
            return httpx.Response(200, content=payloads[artifact_id])

        return GithubService(client=client_with(handler))

    def test_downloads_every_coverage_artifact_of_the_latest_run(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", "fake-token")
        requested: list[int] = []
        service = self.service(
            [
                artifact(1, "frontend-coverage", run=100),
                artifact(2, "backend-coverage", run=100),
                artifact(3, "build-logs", run=100),
                artifact(4, "backend-coverage", run=99),  # run anterior: fica de fora
            ],
            {1: b"front", 2: b"back", 4: b"old"},
            requested,
        )

        zips = service.fetch_latest_coverage_artifact_zips("octocat", "Hello-World")

        assert zips == [b"front", b"back"]
        assert requested == [1, 2]

    def test_without_run_information_only_the_newest_artifact_is_used(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", "fake-token")
        requested: list[int] = []
        service = self.service(
            [artifact(1, "frontend-coverage", run=None), artifact(2, "backend-coverage", run=None)],
            {1: b"front", 2: b"back"},
            requested,
        )

        assert service.fetch_latest_coverage_artifact_zips("octocat", "Hello-World") == [b"front"]
        assert requested == [1]

    def test_expired_artifacts_are_skipped(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", "fake-token")
        requested: list[int] = []
        service = self.service(
            [artifact(1, "frontend-coverage", run=100, expired=True), artifact(2, "backend-coverage", run=100)],
            {2: b"back"},
            requested,
        )

        assert service.fetch_latest_coverage_artifact_zips("octocat", "Hello-World") == [b"back"]

    def test_the_number_of_artifacts_is_capped(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", "fake-token")
        monkeypatch.setattr(settings, "max_coverage_artifacts", 2)
        requested: list[int] = []
        service = self.service(
            [artifact(index, f"part-{index}-coverage", run=100) for index in range(1, 6)],
            {index: b"x" for index in range(1, 6)},
            requested,
        )

        assert len(service.fetch_latest_coverage_artifact_zips("octocat", "Hello-World")) == 2
        assert requested == [1, 2]

    def test_one_oversized_artifact_does_not_discard_the_others(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", "fake-token")
        monkeypatch.setattr(settings, "max_artifact_mb", 1)
        requested: list[int] = []
        service = self.service(
            [artifact(1, "frontend-coverage", run=100), artifact(2, "backend-coverage", run=100)],
            {1: b"x" * (2 * 1024 * 1024), 2: b"back"},
            requested,
        )

        assert service.fetch_latest_coverage_artifact_zips("octocat", "Hello-World") == [b"back"]

    def test_without_a_token_nothing_is_requested(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", None)
        requested: list[int] = []
        service = self.service([artifact(1, "backend-coverage", run=100)], {1: b"x"}, requested)

        assert service.fetch_latest_coverage_artifact_zips("octocat", "Hello-World") == []
        assert requested == []


class TestCombiningArtifacts:
    def test_backend_xml_and_frontend_lcov_are_combined_by_lines(self):
        backend = zip_with({"coverage.xml": XML_BACKEND})  # 900 de 1000
        frontend = zip_with({"lcov.info": "LF:200\nLH:100\n"})  # 100 de 200

        value = read_coverage_from_artifact_zips([backend, frontend])

        assert round(value or 0, 2) == 83.33

    def test_inside_one_artifact_xml_wins_over_lcov_instead_of_double_counting(self):
        both = zip_with({"coverage.xml": XML_BACKEND, "lcov.info": "LF:100\nLH:0\n"})

        assert read_coverage_from_artifact_zips([both]) == 90.0

    def test_a_corrupted_artifact_does_not_break_the_others(self):
        good = zip_with({"coverage.xml": XML_BACKEND})

        assert read_coverage_from_artifact_zips([b"not a zip", good]) == 90.0

    def test_no_artifacts_means_not_available(self):
        assert read_coverage_from_artifact_zips([]) is None


def write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def two_module_project(root: Path, import_line: str) -> None:
    write(root, "packages/web/src/a.ts", f"{import_line}\n")
    write(root, "packages/web/src/b.ts", "export const b = 1;\n")


class TestTsconfigExtends:
    def test_inherits_paths_from_a_base_config_in_another_directory(self, tmp_path):
        write(tmp_path, "tsconfig.base.json", '{"compilerOptions": {"paths": {"@app/*": ["packages/web/src/*"]}}}')
        write(tmp_path, "packages/web/tsconfig.json", '{"extends": "../../tsconfig.base.json"}')
        two_module_project(tmp_path, "import { b } from '@app/b';")

        # paths sem baseUrl são relativos ao tsconfig que os definiu (o base, na raiz)
        assert coupling.calculate_average_instability(tmp_path, ["typescript"]) == 0.5

    def test_the_json_extension_is_optional_like_in_typescript(self, tmp_path):
        write(tmp_path, "tsconfig.base.json", '{"compilerOptions": {"baseUrl": "packages/web/src"}}')
        write(tmp_path, "packages/web/tsconfig.json", '{"extends": "../../tsconfig.base"}')
        two_module_project(tmp_path, "import { b } from 'b';")

        assert coupling.calculate_average_instability(tmp_path, ["typescript"]) == 0.5

    def test_the_child_overrides_the_parent_paths(self, tmp_path):
        write(tmp_path, "tsconfig.base.json", '{"compilerOptions": {"paths": {"@x/*": ["nowhere/*"]}}}')
        write(
            tmp_path,
            "packages/web/tsconfig.json",
            '{"extends": "../../tsconfig.base.json", "compilerOptions": {"paths": {"@x/*": ["./src/*"]}}}',
        )
        two_module_project(tmp_path, "import { b } from '@x/b';")

        assert coupling.calculate_average_instability(tmp_path, ["typescript"]) == 0.5

    def test_follows_a_chain_and_a_list_of_extends(self, tmp_path):
        write(tmp_path, "root.json", '{"compilerOptions": {"baseUrl": "packages/web/src"}}')
        write(tmp_path, "mid.json", '{"extends": "./root.json"}')
        write(tmp_path, "packages/web/tsconfig.json", '{"extends": ["./../../mid.json"]}')
        two_module_project(tmp_path, "import { b } from 'b';")

        assert coupling.calculate_average_instability(tmp_path, ["typescript"]) == 0.5

    def test_ignores_extends_that_point_to_npm_packages(self, tmp_path):
        write(tmp_path, "packages/web/tsconfig.json", '{"extends": "@tsconfig/node18/tsconfig.json"}')
        two_module_project(tmp_path, "import { b } from '@app/b';")

        assert coupling.calculate_average_instability(tmp_path, ["typescript"]) is None

    def test_survives_cycles_and_missing_parents(self, tmp_path):
        write(tmp_path, "a.json", '{"extends": "./b.json"}')
        write(tmp_path, "b.json", '{"extends": "./a.json"}')
        write(tmp_path, "packages/web/tsconfig.json", '{"extends": ["../../a.json", "./missing.json"]}')
        two_module_project(tmp_path, "import { b } from './b';")

        # sem alias nenhum, o import relativo continua funcionando
        assert coupling.calculate_average_instability(tmp_path, ["typescript"]) == 0.5

    def test_stops_following_after_the_depth_limit(self, tmp_path):
        for index in range(8):
            write(tmp_path, f"c{index}.json", f'{{"extends": "./c{index + 1}.json"}}')
        write(tmp_path, "c8.json", '{"compilerOptions": {"baseUrl": "packages/web/src"}}')
        write(tmp_path, "packages/web/tsconfig.json", '{"extends": "../../c0.json"}')
        two_module_project(tmp_path, "import { b } from 'b';")

        # a base está 9 níveis acima: além do limite, não é seguida (e nada quebra)
        assert coupling.calculate_average_instability(tmp_path, ["typescript"]) is None
