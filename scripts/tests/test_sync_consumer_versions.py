"""Regression coverage for maintained consumer release pins."""

from pathlib import Path

import pytest
from sync_consumer_versions import synchronize


@pytest.fixture
def consumer_files(tmp_path: Path) -> dict[str, str]:
    """Create consumer manifests with custom settings that must survive synchronization."""
    (tmp_path / "Cargo.toml").write_text('[workspace.package]\nversion = "3.12.3"\n')
    files = {
        "test_apps/dart/pubspec.yaml": "dependencies:\n  h2m: ^3.12.2\n  ffi: ^2.2.0\n",
        "test_apps/elixir/mix.exs": '{:html_to_markdown, "~> 3.12.2"}, {:rustler, "~> 0.38"}\n',
        "test_apps/kotlin_android/build.gradle.kts": (
            'implementation("io.xberg:html-to-markdown-android:3.12.2")\n'
            'val aarCoord = "io.xberg:html-to-markdown-android:3.12.2"\n'
            'tasks.register("buildHostJni") { custom() }\n'
        ),
    }
    for relative_path, text in files.items():
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True)
        path.write_text(text)
    return files


def test_sync_preserves_custom_content_and_is_idempotent(tmp_path: Path, consumer_files: dict[str, str]) -> None:
    """Update every pin while leaving custom consumer configuration untouched."""
    assert synchronize(tmp_path) is False
    for relative_path, text in consumer_files.items():
        assert (tmp_path / relative_path).read_text() == text.replace("3.12.2", "3.12.3")
    assert synchronize(tmp_path) is True
    assert synchronize(tmp_path, check=True) is True


def test_check_detects_drift_without_modifying_manifests(tmp_path: Path, consumer_files: dict[str, str]) -> None:
    """Reject stale versions without rewriting any file in check mode."""
    assert synchronize(tmp_path, check=True) is False
    for relative_path, text in consumer_files.items():
        assert (tmp_path / relative_path).read_text() == text


def test_missing_pin_fails_before_any_manifest_is_written(tmp_path: Path, consumer_files: dict[str, str]) -> None:
    """Reject renamed dependencies before changing even earlier valid manifests."""
    (tmp_path / "test_apps/elixir/mix.exs").write_text("renamed_dependency()\n")
    with pytest.raises(ValueError, match="expected 1 release pins, found 0"):
        synchronize(tmp_path)
    assert (tmp_path / "test_apps/dart/pubspec.yaml").read_text() == consumer_files["test_apps/dart/pubspec.yaml"]
