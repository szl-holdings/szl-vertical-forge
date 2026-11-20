"""Output staging must not follow or overwrite unrelated filesystem entries."""

import importlib

import pytest

from szl_vertical_forge.forge import forge, load_verticals, verify_output, write_output


def test_output_staging_does_not_follow_existing_tmp_symlink(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_bytes(b"must remain unchanged")
    legacy_tmp = output / "RECEIPT.json.tmp"
    legacy_tmp.symlink_to(unrelated)
    result = forge([load_verticals()[0]])

    assert write_output(result, output)["state"] == "WRITTEN"

    assert unrelated.read_bytes() == b"must remain unchanged"
    assert legacy_tmp.is_symlink()
    assert not (output / "RECEIPT.json").is_symlink()
    # The output remains non-destructively written, but its pre-existing
    # untracked symlink must prohibit a complete-population verification.
    verified = verify_output(result, output)
    assert verified["state"] == "INVALID"
    assert verified["unexpected"] == ["RECEIPT.json.tmp"]


def test_verify_output_rejects_expected_artifact_symlink_even_when_bytes_match(tmp_path):
    output = tmp_path / "output"
    result = forge([load_verticals()[0]])
    write_output(result, output)
    receipt = output / "RECEIPT.json"
    copy = output / "untracked-copy.json"
    copy.write_bytes(receipt.read_bytes())
    receipt.unlink()
    receipt.symlink_to(copy)

    verified = verify_output(result, output)
    assert verified["state"] == "INVALID"
    assert verified["missing"] == []
    assert verified["mismatched"] == []
    assert verified["unexpected"] == ["RECEIPT.json", "untracked-copy.json"]
    assert copy.read_bytes() == result["files"]["RECEIPT.json"]


def test_failed_atomic_replace_preserves_target_and_removes_staging(tmp_path, monkeypatch):
    forge_module = importlib.import_module("szl_vertical_forge.forge")
    target = tmp_path / "RECEIPT.json"
    target.write_bytes(b"previous receipt")
    result = forge([load_verticals()[0]])

    def reject_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(forge_module.os, "replace", reject_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        write_output(result, tmp_path)

    assert target.read_bytes() == b"previous receipt"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["RECEIPT.json"]
