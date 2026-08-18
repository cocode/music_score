# Dependency-free music score SVG

This is a deliberately small renderer for engraved-looking, single-staff
melodies. It uses only Python’s standard library and emits plain SVG. Open the
generated `score.svg` in a browser or import it into a vector editor.

The reason for not using an existing one is that I'm reconstructing old manuscripts
and I want to draw them exactly as they were rendered originally. This is
easier to do with my own code. 

Yes, this is vibe coded, and the rest of this readme is AI generated (codex,
if you are curious.)

<hr>

In standard music-notation terminology, the vertical lines attached to note
heads are **stems**. The usually horizontal, sometimes gently sloped connector
joining short notes is a **beam**; all notes in one beamed group share a stem
direction. The renderer uses a white page by default and chooses one common
direction for each beam.

Eighth and sixteenth notes are automatically beamed when adjacent in a group;
an isolated eighth note is drawn with one flag, and an isolated sixteenth note
with two flags.

Key-signature accidentals are also placed on fixed staff positions. For
example, in treble-clef D major, F-sharp is on the top line and C-sharp is in
the third space; they are not interchangeable decorations.

The renderer uses the Unicode segno character `𝄋` with **Noto Music** as its
primary font family. The bundled `NotoMusic-Regular.ttf` is embedded into each
generated SVG, so the segno does not depend on the viewer having the font
installed.

```sh
python example.py
```

To render the best-effort transcription of the supplied historical plate:

```sh
python original_transcription.py
```

That command writes `original_transcription.svg` and prints the note names to
the terminal. The transcription is approximate: the scan is low-resolution,
some stems and noteheads overlap, and the engraving includes ornaments and
rhythmic details that are difficult to distinguish from the image alone.

## JSON and command line

The note data lives in [original_transcription.json](original_transcription.json)
and [example_score.json](example_score.json), not in the drawing code. Render a
file directly with:

```sh
python render_score.py original_transcription.json --print-notes
python render_score.py example_score.json -o example.svg
```

Multiple files are accepted; their systems are appended in command-line order:

```sh
python render_score.py part-one.json part-two.json -o combined.svg
```

A file containing one system directly—`number`, `no_label`, `key`, `time`, and
`bars` at the top level—is also accepted.

If `-o`/`--output` is omitted, the input basename is used: `top_line.json`
becomes `top_line.svg`.

The compact JSON note form is `"PITCH:DURATION"`, for example
`"A4:8"` for an eighth note or `"C5:4"` for a quarter note. A bar can also
carry `final`, `repeat_start`, `repeat_end`, `repeat_both`, `segno`, and `rehearsal` fields. For a
visible local accidental or a rest, use an object such as
`{"pitch": "F4", "duration": 8, "accidental": "♮"}` or
`{"duration": 4, "rest": true}`.

The basic model is `Score` → `System` → `Bar` → `Note`:

```python
from music_score import Bar, Note, Score, System

score = Score([
    System([
        Bar([Note("G4", 8), Note("A4", 8), Note("B4", 8), Note("D5", 8)]),
        Bar([Note("C5", 4), Note("B4", 8), Note("A4", 8)], final=True),
    ], number="1.", key="F#", time="3/8"),
], title="A little waltz")

score.write_svg("my-score.svg")
```

Supported durations are whole, half, quarter, eighth, and sixteenth notes.
Use `Note("F#4", 8)` or `Note("Bb4", 4)` for accidentals, and
`Note(duration=4, rest=True)` for a rest. `Bar` supports `repeat_start`,
`repeat_end`, `final`, and a small text annotation through `rehearsal`.

The renderer uses the Unicode treble-clef and accidental symbols with common
music-font fallbacks. If your browser does not have a music font installed,
installing a font such as Bravura or Noto Music will improve those symbols;
the staff, noteheads, stems, beams, ledger lines, and barlines remain ordinary
SVG shapes.
