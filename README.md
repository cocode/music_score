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

Set `"show_time": false` on a continuation system to retain its meter in the
data without printing the time signature again. The reclaimed horizontal
space is used for the notes.

If `-o`/`--output` is omitted, the input basename is used: `top_line.json`
becomes `top_line.svg`.

The compact JSON note form is `"PITCH:DURATION"`, for example
`"A4:8"` for an eighth note, `"C5:4"` for a quarter note, or `"G♮5:16"`
for a sixteenth note with a displayed natural sign. Append one or more periods
for augmentation dots: `"A5:8."` is dotted and `"A5:8.."` is double-dotted.
Append `!` to a compact note for staccato, as in `"A4:8!"`, or `'` for the
historical staccatissimo stroke, as in `"A4:8'"`. Use `>` for a single-note
accent, as in `"A4:8>"`. A note object can
also set `staccato: true` for the long form. Downward-stem staccato dots are
placed above the staff, or above the note when the note is already above the
staff. Accents are drawn below the staff to match the historical source; `<`
is accepted as the mirrored accent glyph. A bar can also
carry `final`, `repeat`, `segno`, `slurs`,
and `rehearsal` fields. `final` draws a thin-plus-thick ending barline. For a
visible local accidental or a rest, use an object such as
`{"pitch": "F4", "duration": 8, "accidental": "♮"}` or
`{"duration": 4, "rest": true}`.

Slurs are represented as bar-local spans of note indices. The short form uses
`{"above": "0:2"}` or `{"below": "0:2"}`; indices are zero-based and
inclusive. This places a slur over the first three notes:

```json
{
  "notes": [
    "A4:8!",
    "B4:8",
    "C5:8"
  ],
  "slurs": [{"above": "0:2"}]
}
```

The object form `{"start": 0, "end": 2, "placement": "above"}` remains
supported. Compact note modifiers can be combined, for example
`"A4:8.!'>|"` means dotted, staccato, staccatissimo, accented, and a beam
break after the note.

The current renderer supports slurs within one bar. Cross-bar slurs can be
added later with the same span idea using bar-and-note references. Slurs
automatically move away from noteheads and upward stems/beams when needed.

The long form uses an integer `dots` field, such as
`{"pitch": "A5", "duration": 8, "dots": 2}` for the same double-dotted
eighth note as `"A5:8.."`.

Visible accidentals automatically reserve extra horizontal space before their
notes. Accidentals supplied by the key signature are suppressed and do not
consume this space unless explicitly requested.

Repeat signs use the standard two central dots by default. Set
`"repeat_dots": 4` on a bar with `"repeat": "start"`, `"end"`, or `"both"`
to reproduce the historical variant with one dot in every staff space.

Use `"repeat": "end"` for `:||`, `"repeat": "start"` for `||:`, and
`"repeat": "both"` for `:||:`. The `end` and `both` forms attach to the
annotated bar's ending boundary; `start` belongs before the annotated bar.

To end a beam group after a particular eighth or sixteenth note, append `|` to
the compact form, as in `"A4:8|"`. Put it after augmentation dots when both
are needed: `"A5:8.|"`. The equivalent object form uses
`"beam_break_after": true`:

```json
{"notes": [
  "E5:8",
  {"pitch": "A4", "duration": 8, "beam_break_after": true},
  "E5:16",
  "G5:16"
]}
```

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
Use `Note("F#4", 8)` or `Note("B♭4", 4)` for accidentals, and
`Note(duration=4, rest=True)` for a rest. `Bar` supports `repeat`, `final`,
and a small text annotation through `rehearsal`.

The renderer uses the Unicode treble-clef and accidental symbols with common
music-font fallbacks. If your browser does not have a music font installed,
installing a font such as Bravura or Noto Music will improve those symbols;
the staff, noteheads, stems, beams, ledger lines, and barlines remain ordinary
SVG shapes.
