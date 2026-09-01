"""Sanity del andamiaje."""

from pathlib import Path


def test_carpetas_de_tests_existen() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "mockups" / "golden_svg").is_dir()
    assert (root / "mockups" / "profiles").is_dir()
    assert (root / "mockups" / "matrices").is_dir()
    assert (root / "unit_tests").is_dir()
    assert (root / "integration_tests").is_dir()
