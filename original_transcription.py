"""Best-effort transcription of the two melodies in the supplied plate.

Run this file to create ``original_transcription.svg`` and print the note
names used.  The scan is an engraved historical image, not a clean source for
optical music recognition, so a handful of pitches/rhythmic groupings are
necessarily approximate.  The note spellings are still useful as a starting
point for correcting the transcription by ear or against a higher-resolution
scan.
"""

from __future__ import annotations

from music_score import Bar, Note, Score, System


def note_list(*tokens: str) -> list[Note]:
    """Parse compact ``PITCH:DURATION`` tokens used below."""
    result: list[Note] = []
    for token in tokens:
        pitch, duration = token.rsplit(":", 1)
        # The plate is in D major. F# and C# are supplied by the key signature;
        # suppressing their local glyphs makes the output look like the plate.
        implied = "" if pitch[0].upper() in {"F", "C"} and "#" in pitch else None
        result.append(Note(pitch, int(duration), accidental=implied))
    return result


def bar(*tokens: str, **kwargs: object) -> Bar:
    return Bar(note_list(*tokens), **kwargs)


def tune_one() -> list[System]:
    """Approximate transcription of No. 1, including its Da Capo ending."""
    return [
        System([
            bar("A4:8", "B4:8", "D5:8"),
            bar("B4:8", "D5:8", "F#5:8"),
            bar("D5:8", "E5:8", "F#5:8"),
            bar("D5:8", "B4:8", "A4:8"),
        ], number="1.", key="D", time="3/8"),
        System([
            bar("G4:8", "B4:8", "D5:8"),
            bar("C5:8", "B4:8", "A4:8"),
            bar("D5:8", "C5:8", "B4:8"),
            bar("A4:8", "G4:8", "F#4:8"),
        ], key="D", time="3/8"),
        System([
            bar("A4:8", "B4:8", "C5:8"),
            bar("D5:8", "C5:8", "B4:8"),
            bar("A4:8", "B4:8", "C5:8"),
            bar("D5:8", "C5:8", "B4:8"),
        ], key="D", time="3/8"),
        System([
            bar("C5:8", "B4:8", "A4:8", "G4:8", "F#4:8", "E4:8"),
            bar("D5:8", "C5:8", "B4:8"),
            bar("A4:8", "B4:8", "C5:8"),
            bar("B4:8", "A4:8", "G4:8", rehearsal="Fine."),
        ], key="D", time="3/8"),
        System([
            bar("G4:8", "A4:8", "B4:8"),
            bar("C5:8", "D5:8", "E5:8"),
            bar("F#5:8", "E5:8", "D5:8"),
            bar("C5:8", "B4:8", "A4:8", final=True, rehearsal="Da Capo."),
        ], key="D", time="3/8"),
    ]


def tune_two() -> list[System]:
    """Approximate transcription of No. 2, including its Dal Segno ending."""
    return [
        System([
            bar("D5:8", "C#5:8", "B4:8", "A4:8", "B4:8", "C#5:8"),
            bar("D5:8", "E5:8", "F#5:8"),
            bar("E5:8", "D5:8", "C#5:8"),
            bar("B4:8", "A4:8", "G4:8", "F#4:8"),
        ], number="2.", key="D", time="3/8"),
        System([
            bar("G4:8", "A4:8", "B4:8", "C#5:8", "D5:8", "E5:8"),
            bar("F#5:8", "E5:8", "D5:8", "C#5:8"),
            bar("B4:8", "C#5:8", "D5:8", "E5:8", "F#5:8"),
            bar("E5:8", "D5:8", "C#5:8", "B4:8"),
        ], key="D", time="3/8"),
        System([
            bar("A4:8", "B4:8", "C#5:8", "D5:8", "E5:8", "F#5:8"),
            bar("E5:8", "D5:8", "C#5:8", "B4:8", "A4:8", "G4:8"),
            bar("A4:8", "B4:8", "C#5:8", "D5:8", "E5:8", "F#5:8"),
            bar("G5:8", "F#5:8", "E5:8", "D5:8", "C#5:8", "B4:8"),
        ], key="D", time="3/8"),
        System([
            bar("A4:8", "B4:8", "C#5:8", "D5:8", "E5:8", "F#5:8"),
            bar("G5:8", "F#5:8", "E5:8", "D5:8", "C#5:8", "B4:8"),
            bar("A4:8", "B4:8", "C#5:8", "D5:8", "E5:8", "F#5:8"),
            bar("F#5:8", "E5:8", "D5:8", "C#5:8", "B4:8", "A4:8", final=True, rehearsal="Dal Segno."),
        ], key="D", time="3/8"),
    ]


def print_notes(name: str, systems: list[System]) -> None:
    print(name)
    for line_number, system in enumerate(systems, 1):
        bars = []
        for current_bar in system.bars:
            bars.append(" ".join(f"{n.pitch}/{n.duration}" for n in current_bar.notes))
        print(f"  line {line_number}:  " + " | ".join(bars))


def main() -> None:
    first = tune_one()
    second = tune_two()
    Score(
        first + second,
        title="Tunes adapted to the French Slow Waltz.",
        subtitle="Approximate note transcription of the supplied historical plate",
        footer="No. 1: Da Capo.    No. 2: Dal Segno.",
        system_gap=68,
    ).write_svg("original_transcription.svg")
    print_notes("No. 1", first)
    print_notes("No. 2", second)
    print("\nwrote original_transcription.svg")


if __name__ == "__main__":
    main()
