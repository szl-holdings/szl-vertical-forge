"""Executable contract for deterministic, fail-closed forge artifacts."""

import copy
import json
from pathlib import Path

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
    "712c20ee1ab8be96b2d8ec7cba120321fb2e2487872c2ce088fce39353e97571"
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


def test_receipt_chain_recomputes_and_rejects_tampering():
    receipt = forge()["receipt"]
    assert verify_receipt(receipt)["state"] == "VERIFIED"
    tampered = copy.deepcopy(receipt)
    tampered["events"][1]["artifact_sha256"] = "f" * 64
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
    assert VERSION == "0.2.1"
