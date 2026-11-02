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
    assert verify_output(result, output)["state"] == "VERIFIED_LOCAL_ARTIFACTS"


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
