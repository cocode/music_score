"""Compatibility wrapper for the JSON-backed historical transcription."""

from pathlib import Path

from render_score import main as render_main


if __name__ == "__main__":
    source = Path(__file__).with_name("original_transcription.json")
    raise SystemExit(render_main([str(source), "--output", "original_transcription.svg", "--print-notes"]))
