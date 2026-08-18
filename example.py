"""Compatibility wrapper for the JSON-backed example score."""

from pathlib import Path

from render_score import main as render_main


if __name__ == "__main__":
    source = Path(__file__).with_name("example_score.json")
    raise SystemExit(render_main([str(source), "--output", "score.svg"]))
