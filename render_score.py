"""Command-line JSON loader for :mod:`music_score`.

Examples::

    python render_score.py original_transcription.json -o original.svg
    python render_score.py example_score.json -o example.svg
    python render_score.py part-one.json part-two.json -o combined.svg
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from music_score import Bar, Note, Score, Style, System


def _note(value: Any, key: str) -> Note:
    """Convert a JSON note string or object into a ``Note``."""
    if isinstance(value, str):
        pitch, duration = value.rsplit(":", 1)
        data: dict[str, Any] = {"pitch": pitch, "duration": int(duration)}
    elif isinstance(value, dict):
        data = dict(value)
    else:
        raise ValueError(f"note must be a string or object, got {value!r}")

    pitch = str(data.get("pitch", "B4"))
    accidental = data.get("accidental")
    # In D major, these accidentals are already present in the key signature.
    # An explicit accidental field still wins, so JSON can request a visible
    # natural/sharp/flat when needed.
    if accidental is None and key == "D" and pitch[:2] in {"F#", "C#"}:
        accidental = ""
    return Note(
        pitch=pitch,
        duration=int(data.get("duration", 4)),
        accidental=accidental,
        rest=bool(data.get("rest", False)),
    )


def score_from_dict(data: dict[str, Any]) -> Score:
    systems: list[System] = []
    # Accept the full page format and the convenient single-system format
    # shown in the README and transcription examples.
    system_data_list = data.get("systems")
    if system_data_list is None and "bars" in data:
        system_data_list = [data]
    for system_data in system_data_list or []:
        key = str(system_data.get("key", data.get("key", "D")))
        bars: list[Bar] = []
        for bar_data in system_data.get("bars", []):
            if isinstance(bar_data, list):
                note_data = bar_data
                options: dict[str, Any] = {}
            else:
                note_data = bar_data.get("notes", [])
                options = bar_data
            bars.append(Bar(
                [_note(value, key) for value in note_data],
                repeat_start=bool(options.get("repeat_start", False)),
                repeat_end=bool(options.get("repeat_end", False)),
                segno=bool(options.get("segno", False)),
                final=bool(options.get("final", False)),
                rehearsal=options.get("rehearsal"),
            ))
        systems.append(System(
            bars,
            number=system_data.get("number"),
            no_label=bool(system_data.get("no_label", False)),
            clef=str(system_data.get("clef", data.get("clef", "treble"))),
            key=key,
            time=str(system_data.get("time", data.get("time", "3/8"))),
            label=system_data.get("label"),
        ))

    style_data = dict(data.get("style", {}))
    style = Style(**style_data)
    score_options = {
        "title": data.get("title"),
        "subtitle": data.get("subtitle"),
        "footer": data.get("footer"),
        "style": style,
        "system_gap": float(data.get("system_gap", 87.0)),
    }
    return Score(systems, **score_options)


def score_from_file(filename: str | Path) -> Score:
    path = Path(filename)
    with path.open(encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return score_from_dict(data)


def _combine_scores(scores: Sequence[Score]) -> Score:
    """Concatenate systems from multiple files, using the first page settings."""
    if not scores:
        raise ValueError("at least one score file is required")
    first = scores[0]
    systems = [system for score in scores for system in score.systems]
    return Score(
        systems,
        title=first.title,
        subtitle=first.subtitle,
        footer=first.footer,
        style=first.style,
        system_gap=first.system_gap,
    )


def _print_notes(scores: Sequence[Score]) -> None:
    for score_index, score in enumerate(scores, 1):
        if len(scores) > 1:
            print(f"file {score_index}")
        for line_number, system in enumerate(score.systems, 1):
            bars = []
            for bar in system.bars:
                bars.append(" ".join(f"{note.pitch}/{note.duration}" for note in bar.notes))
            print(f"  line {line_number}: " + " | ".join(bars))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render one or more music-score JSON files as SVG.")
    parser.add_argument("files", nargs="+", help="JSON score files; systems are concatenated in order")
    parser.add_argument("-o", "--output", default=None, help="output SVG path (default: input base name with .svg)")
    parser.add_argument("--print-notes", action="store_true", help="print pitch/duration tokens while rendering")
    args = parser.parse_args(argv)

    scores = [score_from_file(filename) for filename in args.files]
    score = _combine_scores(scores)
    output = args.output or str(Path(args.files[0]).with_suffix(".svg"))
    score.write_svg(output)
    if args.print_notes:
        _print_notes(scores)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
