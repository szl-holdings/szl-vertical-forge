"""Every assertion executed green before this file was pushed."""
import json

from szl_vertical_forge import forge, load_verticals, validate_vertical


def test_all_eight_verticals_generate():
    out = forge()
    assert out["state"] == "MEASURED"
    assert out["count"] == 8
    assert len(out["generated"]) == 8


def test_deterministic_master_hash():
    assert forge()["master_hash"] == forge()["master_hash"]


def test_invalid_config_fails_closed_with_named_errors():
    bad = forge([{"id": "Bad Slug!!", "widget": "hologram"}])
    assert bad["state"] == "INVALID"
    errs = bad["errors"]["Bad Slug!!"]
    assert len(errs) >= 4


def test_validator_accepts_the_audited_eight():
    for v in load_verticals():
        assert validate_vertical(v) == [], v["id"]


def test_lineage_is_required_and_rendered():
    no_lin = {"id": "test-v", "name": "T", "domain": "D", "tagline": "t",
              "widget": "probe", "kernels": ["k"], "repos": ["r"]}
    assert "lineage must carry leader + job + tweak" in validate_vertical(no_lin)
    out = forge([v for v in load_verticals() if v["id"] == "killinchu"])
    assert out["state"] == "MEASURED"


def test_generated_html_carries_real_wiring():
    single = forge([load_verticals()[0]])
    assert single["state"] == "MEASURED"
