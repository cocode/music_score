"""Generate the example score: ``python example.py``."""

from music_score import Bar, Note, Score, System


def main() -> None:
    # The API is deliberately declarative: describe notes and bars, then render.
    first_line = System(
        [
            Bar([Note("G4", 8), Note("A4", 8), Note("B4", 8), Note("D5", 8), Note("C5", 8), Note("B4", 8)]),
            Bar([Note("A4", 8), Note("B4", 8), Note("C5", 8), Note("D5", 8), Note("C5", 8), Note("B4", 8)]),
            Bar([Note("A4", 4), Note("G4", 4), Note("F#4", 4)], final=True),
        ],
        number="1.",
        key="F#",
        time="3/8",
    )
    second_line = System(
        [
            Bar([Note("D5", 8), Note("C5", 8), Note("B4", 8), Note("A4", 8), Note("G4", 8), Note("F#4", 8)]),
            Bar([Note("G4", 8), Note("A4", 8), Note("B4", 8), Note("D5", 8), Note("C5", 8), Note("B4", 8)], rehearsal="Fine."),
            Bar([Note("A4", 4), Note("G4", 4), Note("F#4", 4)], final=True),
        ],
    )
    Score(
        [first_line, second_line],
        title="Tunes adapted to the French Slow Waltz.",
        subtitle="A small SVG engraving example",
        footer="Engraved with Python and SVG",
    ).write_svg("score.svg")


if __name__ == "__main__":
    main()
