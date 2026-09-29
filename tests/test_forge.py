"""Executable contract for deterministic, fail-closed forge artifacts."""

import copy
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from szl_vertical_forge import (
    forge,
    load_verticals,
    validate_vertical,
    verify_output,
    verify_receipt,
    write_output,
)
from szl_vertical_forge.forge import VERSION, main

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MASTER_HASH = (
    "117dd82061d3be114fe1e5207bae68a6e754514af8121e9b01abd89b53d3f0c9"
)


def test_all_eight_verticals_generate_with_complete_artifacts():
    result = forge()
    assert result["state"] == "MEASURED_LOCAL_BUILD"
    assert result["count"] == 8
    assert len(result["generated"]) == 8
    assert len(result["files"]) == 17
    assert len(result["master_hash"]) == 64


def test_deterministic_master_hash_and_bytes():
    first = forge()
    second = forge()
    assert first["master_hash"] == second["master_hash"]
    assert first["master_hash"] == EXPECTED_MASTER_HASH
    assert first["files"] == second["files"]


def test_invalid_config_fails_closed_with_named_errors():
    result = forge([{"id": "Bad Slug!!", "widget": "hologram"}])
    assert result["state"] == "INVALID"
    assert len(result["errors"]["Bad Slug!!"]) >= 8


def test_validator_accepts_the_audited_eight():
    for vertical in load_verticals():
        assert validate_vertical(vertical) == [], vertical["id"]


def test_lineage_is_required_and_rendered():
    vertical = copy.deepcopy(load_verticals()[0])
    vertical.pop("lineage")
    assert (
        "lineage must carry leader + job + tweak + HTTPS sources"
        in validate_vertical(vertical)
    )
    page = forge([load_verticals()[0]])["files"]["killinchu/index.html"].decode()
    assert "Anduril Lattice" in page
    assert "Take the job, never proprietary code" in page
    assert "https://www.anduril.com/news/jiatf-401" in page


def test_generated_html_carries_runtime_and_receipt_wiring():
    terra = next(item for item in load_verticals() if item["id"] == "terra")
    page = forge([terra])["files"]["terra/index.html"].decode()
    assert 'const EP="/api/live"' in page
    assert 'href="/panels"' in page
    assert 'href="/build-receipt.json"' in page
    assert "OBSERVED - HTTP" in page
    assert "Reachability alone is not a domain measurement" in page


def test_every_generated_browser_script_parses_and_styles_are_unescaped():
    node = shutil.which("node")
    assert node is not None, "Node.js is required to validate generated browser scripts"
    for path, artifact in forge()["files"].items():
        if not path.endswith("index.html"):
            continue
        page = artifact.decode("utf-8")
        style = re.search(r"<style>(.*?)</style>", page, re.S).group(1)
        assert ":root{--bg:" in style, path
        assert "{{" not in style, path
        scripts = re.findall(r"<script>(.*?)</script>", page, re.S)
        assert scripts, path
        for script in scripts:
            checked = subprocess.run(
                [node, "--check"], input=script, text=True,
                encoding="utf-8", capture_output=True, timeout=15,
            )
            assert checked.returncode == 0, f"{path}: {checked.stderr}"


def test_template_like_text_is_not_interpreted_as_another_placeholder():
    vertical = copy.deepcopy(load_verticals()[0])
    vertical["tagline"] = "Keep {{braces}} and {endpoint_js} as text"
    page = forge([vertical])["files"]["killinchu/index.html"].decode()
    assert "Keep {{braces}} and {endpoint_js} as text" in page


def test_receipt_chain_recomputes_and_rejects_tampering():
    receipt = forge()["receipt"]
    assert verify_receipt(receipt)["state"] == "VERIFIED"
    tampered = copy.deepcopy(receipt)
    tampered["events"][1]["artifact_sha256"] = "f" * 64
    assert verify_receipt(tampered)["state"] == "INVALID"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("config_sha256", "e" * 64),
        ("generator", "szl-vertical-forge/9.9.9"),
        ("algorithm", "sha256-something-else"),
        ("genesis", "1" * 64),
    ],
)
def test_receipt_header_mutation_is_not_verified(field, value):
    receipt = forge()["receipt"]
    tampered = copy.deepcopy(receipt)
    tampered[field] = value
    assert tampered["events"] == receipt["events"]
    assert tampered["master_hash"] == receipt["master_hash"]
    assert verify_receipt(tampered)["state"] == "INVALID"


def test_receipt_header_fields_are_required():
    receipt = forge()["receipt"]
    for field in ("generator", "algorithm", "genesis", "config_sha256"):
        tampered = copy.deepcopy(receipt)
        del tampered[field]
        assert verify_receipt(tampered)["state"] == "INVALID"


def test_receipt_config_must_match_independent_authority():
    receipt = forge()["receipt"]
    assert (
        verify_receipt(receipt, expected_config_sha256=receipt["config_sha256"])["state"]
        == "VERIFIED"
    )
    assert verify_receipt(receipt, expected_config_sha256="0" * 64)["state"] == "INVALID"


def test_receipt_master_hash_is_not_the_bare_chain_tip():
    receipt = forge()["receipt"]
    assert receipt["chain_tip"] == receipt["events"][-1]["chain_hash"]
    assert receipt["master_hash"] != receipt["chain_tip"]
    tampered = copy.deepcopy(receipt)
    tampered["master_hash"] = tampered["chain_tip"]
    assert verify_receipt(tampered)["state"] == "INVALID"


def test_generate_write_and_verify_round_trip(tmp_path):
    result = forge()
    assert write_output(result, tmp_path)["state"] == "WRITTEN"
    verified = verify_output(result, tmp_path)
    assert verified["state"] == "VERIFIED_LOCAL_ARTIFACTS"
    assert verified["files_checked"] == 17
    disk_receipt = json.loads((tmp_path / "RECEIPT.json").read_text(encoding="utf-8"))
    assert verify_receipt(disk_receipt)["state"] == "VERIFIED"


def test_verify_output_detects_artifact_tampering(tmp_path):
    result = forge()
    write_output(result, tmp_path)
    (tmp_path / "terra" / "index.html").write_text("tampered", encoding="utf-8")
    verified = verify_output(result, tmp_path)
    assert verified["state"] == "INVALID"
    assert verified["mismatched"] == ["terra/index.html"]


def test_committed_distribution_matches_the_generator():
    verified = verify_output(forge(), ROOT / "dist")
    assert verified["state"] == "VERIFIED_LOCAL_ARTIFACTS"
    assert verified["master_hash"] == EXPECTED_MASTER_HASH


def test_endpoint_validation_closes_credentials_fragments_and_protocol_relative_urls():
    vertical = copy.deepcopy(load_verticals()[0])
    endpoints = (
        "//example.com/api",
        "http://example.com/api",
        "https://u:p@example.com/api",
        "https://example.com/api#x",
    )
    for endpoint in endpoints:
        vertical["endpoint"] = endpoint
        assert (
            "endpoint must be a safe root-relative path or HTTPS URL"
            in validate_vertical(vertical)
        )


def test_lineage_sources_are_required_and_https_only():
    vertical = copy.deepcopy(load_verticals()[0])
    vertical["lineage"]["sources"] = ["http://example.com/source"]
    assert (
        "lineage must carry leader + job + tweak + HTTPS sources"
        in validate_vertical(vertical)
    )


def test_html_escapes_audited_text():
    vertical = copy.deepcopy(load_verticals()[0])
    vertical["tagline"] = '<img src=x onerror="boom">'
    page = forge([vertical])["files"]["killinchu/index.html"].decode()
    assert "<img src=x" not in page
    assert "&lt;img src=x" in page


def test_cli_generates_and_then_verifies_selected_vertical(tmp_path, capsys):
    assert main(["generate", "--vertical", "terra", "--output-dir", str(tmp_path)]) == 0
    generated = json.loads(capsys.readouterr().out)
    assert generated["state"] == "VERIFIED_LOCAL_ARTIFACTS"
    assert generated["vertical_count"] == 1
    assert main(["verify", "--vertical", "terra", "--output-dir", str(tmp_path)]) == 0


def test_package_version_matches_generator():
    assert VERSION == "0.2.3"
