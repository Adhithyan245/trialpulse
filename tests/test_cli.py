"""Tests for the CLI entry point (Task T08)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from trialpulse.agent.llm import LLMError
from trialpulse.agent.report import DraftClaim, DraftReport
from trialpulse.__main__ import main


class FakeErrorModel:
    """A JSONModel that raises LLMError."""

    name = "fake-error-model"

    def generate(self, system: str, user: str, schema):
        raise LLMError("simulated LLM failure")


def test_signals_command_lists_signals(capsys):
    """signals --day 15 prints a line containing P-07 and drift."""
    exit_code = main(["signals", "--day", "15"])
    assert exit_code == 0
    captured = capsys.readouterr()
    output = captured.out
    assert "P-07" in output
    assert "drift" in output
    # Check the format: should have P-07, drift type, metric, start, z, cites
    lines = output.strip().split("\n")
    assert len(lines) > 0
    assert any("P-07" in line and "drift" in line for line in lines)


def test_generate_command_writes_file():
    """generate --out <tmp_path file> creates the output file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "trial.json"
        exit_code = main(["generate", "--out", str(out_path)])
        assert exit_code == 0
        assert out_path.exists()
        assert out_path.stat().st_size > 0
        # Verify it's valid JSON
        import json

        data = json.loads(out_path.read_text())
        assert "participants" in data
        assert "readings" in data


def test_report_with_llm_error_exits_2(monkeypatch, capsys):
    """report with GeminiModel raising LLMError exits with code 2."""
    from trialpulse.agent import llm

    monkeypatch.setattr(llm, "GeminiModel", lambda: FakeErrorModel())

    exit_code = main(["report", "P-07", "--day", "15"])
    assert exit_code == 2

    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "simulated LLM failure" in captured.err
