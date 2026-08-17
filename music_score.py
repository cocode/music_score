"""A tiny dependency-free music score renderer.

The module intentionally targets the small, engraved single-staff scores shown
in the reference image rather than trying to be a complete music notation
engine.  It writes ordinary SVG, so the output can be opened in a browser,
edited by hand, or converted to another format with an external tool.

Example::

    from music_score import Bar, Note, Score, System

    system = System(
        bars=[
            Bar([Note("G4", 8), Note("A4", 8), Note("B4", 8), Note("D5", 8)]),
            Bar([Note("C5", 4), Note("B4", 8), Note("A4", 8)]),
        ],
        number="1.",
    )
    Score([system], title="Tunes adapted to the French Slow Waltz.").write_svg(
        "score.svg"
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
import re
from typing import Iterable, Optional, Sequence


PITCHES = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
NATURAL_STEPS = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
DIATONIC_FROM_C = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
NOTE_RE = re.compile(r"^([A-Ga-g])([#b]?)(-?\d+)$")


@dataclass(frozen=True)
class Note:
    """One pitched note.

    ``duration`` is a denominator: 4 is a quarter note, 8 an eighth note,
    and 2 a half note.  A note can also be written as ``Note("F#4", 8)``.
    ``rest=True`` makes a duration-only rest and ignores ``pitch``.
    """

    pitch: str = "B4"
    duration: int = 4
    accidental: Optional[str] = None
    rest: bool = False

    def __post_init__(self) -> None:
        if self.duration not in (1, 2, 4, 8, 16):
            raise ValueError("duration must be one of 1, 2, 4, 8, or 16")
        if not self.rest:
            match = NOTE_RE.match(self.pitch)
            if not match:
                raise ValueError(f"invalid pitch {self.pitch!r}; use e.g. 'F#4'")

    @property
    def parsed(self) -> tuple[str, str, int]:
        match = NOTE_RE.match(self.pitch)
        if not match:
            raise ValueError(f"invalid pitch {self.pitch!r}")
        letter, accidental, octave = match.groups()
        return letter.upper(), accidental, int(octave)

    @property
    def step(self) -> int:
        letter, _, octave = self.parsed
        return (octave - 4) * 7 + DIATONIC_FROM_C[letter] - 2

    @property
    def display_accidental(self) -> str:
        if self.accidental is not None:
            return self.accidental
        return self.parsed[1]


@dataclass
class Bar:
    notes: Sequence[Note]
    repeat_start: bool = False
    repeat_end: bool = False
    final: bool = False
    rehearsal: Optional[str] = None

    def __post_init__(self) -> None:
        self.notes = tuple(self.notes)


@dataclass
class System:
    bars: Sequence[Bar]
    number: Optional[str] = None
    clef: str = "treble"
    key: str = "F#"
    time: str = "3/8"
    label: Optional[str] = None

    def __post_init__(self) -> None:
        self.bars = tuple(self.bars)


@dataclass
class Style:
    """Visual settings, in SVG user units."""

    ink: str = "#34312d"
    paper: str = "#ffffff"
    staff_gap: float = 9.0
    stem: float = 1.6
    staff_width: float = 1.15
    note_width: float = 6.7
    note_height: float = 4.7
    bar_width: float = 1.2
    page_width: float = 900.0
    margin_x: float = 54.0


class SVG:
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height
        self.items: list[str] = []

    def raw(self, value: str) -> None:
        self.items.append(value)

    def line(self, x1: float, y1: float, x2: float, y2: float, **attrs: object) -> None:
        self.items.append(
            f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}"{_attrs(attrs)}/>'
        )

    def path(self, d: str, **attrs: object) -> None:
        self.items.append(f'<path d="{d}"{_attrs(attrs)}/>')

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, **attrs: object) -> None:
        self.items.append(
            f'<ellipse cx="{cx:g}" cy="{cy:g}" rx="{rx:g}" ry="{ry:g}"{_attrs(attrs)}/>'
        )

    def rect(self, x: float, y: float, width: float, height: float, **attrs: object) -> None:
        self.items.append(
            f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}"{_attrs(attrs)}/>'
        )

    def text(self, x: float, y: float, value: str, **attrs: object) -> None:
        self.items.append(f'<text x="{x:g}" y="{y:g}"{_attrs(attrs)}>{escape(value)}</text>')

    def finish(self) -> str:
        body = "\n  ".join(self.items)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width:g}" '
            f'height="{self.height:g}" viewBox="0 0 {self.width:g} {self.height:g}">\n'
            f'  <title>Engraved music score</title>\n  {body}\n</svg>\n'
        )


def _attrs(attrs: dict[str, object]) -> str:
    return "".join(f' {key.replace("_", "-")}="{escape(str(value))}"' for key, value in attrs.items())


class Score:
    """Render one or more systems of a monophonic treble-staff score."""

    def __init__(
        self,
        systems: Sequence[System],
        *,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        footer: Optional[str] = None,
        style: Optional[Style] = None,
        system_gap: float = 87.0,
    ):
        self.systems = tuple(systems)
        self.title = title
        self.subtitle = subtitle
        self.footer = footer
        self.style = style or Style()
        self.system_gap = system_gap

    def svg(self) -> str:
        top = 57.0 if self.title else 25.0
        if self.subtitle:
            top += 23.0
        system_height = 53.0
        footer_height = 37.0 if self.footer else 0.0
        height = top + max(1, len(self.systems)) * (system_height + self.system_gap) - self.system_gap + footer_height + 20
        svg = SVG(self.style.page_width, height)
        ink, paper = self.style.ink, self.style.paper
        svg.rect(0, 0, self.style.page_width, height, fill=paper)
        if self.title:
            svg.text(self.style.page_width / 2, 28, self.title, text_anchor="middle", fill=ink,
                     font_family="Georgia, Times New Roman, serif", font_size=20, font_weight="bold",
                     letter_spacing="0.3")
        if self.subtitle:
            svg.text(self.style.page_width / 2, 48, self.subtitle, text_anchor="middle", fill=ink,
                     font_family="Georgia, Times New Roman, serif", font_size=12, font_style="italic")

        y = top
        for system in self.systems:
            self._draw_system(svg, system, y)
            y += system_height + self.system_gap
        if self.footer:
            svg.text(self.style.page_width / 2, height - 13, self.footer, text_anchor="middle", fill=ink,
                     font_family="Georgia, Times New Roman, serif", font_size=12, font_weight="bold",
                     letter_spacing="0.2")
        return svg.finish()

    def write_svg(self, filename: str) -> None:
        with open(filename, "w", encoding="utf-8") as output:
            output.write(self.svg())

    def _draw_system(self, svg: SVG, system: System, y: float) -> None:
        s = self.style
        ink = s.ink
        left = s.margin_x
        right = s.page_width - s.margin_x
        staff_top = y + 8
        staff_bottom = staff_top + 4 * s.staff_gap

        if system.number:
            svg.text(left - 44, staff_top + 29, system.number, fill=ink,
                     font_family="Georgia, Times New Roman, serif", font_size=19, font_weight="bold")
        if system.label:
            svg.text(left - 4, staff_top - 9, system.label, fill=ink,
                     font_family="Georgia, Times New Roman, serif", font_size=10, font_style="italic")

        for line_no in range(5):
            yy = staff_top + line_no * s.staff_gap
            svg.line(left, yy, right, yy, stroke=ink, stroke_width=s.staff_width, stroke_linecap="round")

        # Unicode music symbols keep the library font-independent at the SVG
        # level while allowing a high-quality installed music font to be used.
        svg.text(left + 7, staff_top + 37, "𝄞", fill=ink,
                 font_family="Bravura, Noto Music, DejaVu Sans, serif", font_size=49)
        key_x = left + 41
        for index, accidental in enumerate(self._key_accidentals(system.key)):
            symbol = "♯" if accidental == "#" else "♭"
            step = (index * 2 + 1) % 7
            svg.text(key_x + index * 10, staff_top + 30 - (step % 3) * 3, symbol, fill=ink,
                     font_family="Bravura, Noto Music, DejaVu Sans, serif", font_size=18)
        time_x = key_x + len(self._key_accidentals(system.key)) * 10 + 16
        if system.time:
            numerator, denominator = system.time.split("/", 1)
            svg.text(time_x, staff_top + 18, numerator, fill=ink, font_family="Georgia, serif", font_size=19, font_weight="bold")
            svg.text(time_x, staff_top + 38, denominator, fill=ink, font_family="Georgia, serif", font_size=19, font_weight="bold")

        content_left = time_x + 26
        content_right = right - 3
        bar_widths = [self._bar_width(bar) for bar in system.bars]
        scale = max(0.65, (content_right - content_left) / max(1, sum(bar_widths)))
        x = content_left
        for bar, natural_width in zip(system.bars, bar_widths):
            width = natural_width * scale
            self._draw_bar(svg, bar, x, width, staff_top)
            x += width

    @staticmethod
    def _key_accidentals(key: str) -> tuple[str, ...]:
        if not key:
            return ()
        count = {"C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5, "F#": 6}.get(key, 1 if key.endswith("#") else 0)
        return tuple("#" for _ in range(count))

    @staticmethod
    def _bar_width(bar: Bar) -> float:
        # Width is intentionally generous, like a nineteenth-century plate:
        # short notes get grouped into visible beams instead of being cramped.
        return max(68.0, 24.0 + sum({1: 30, 2: 25, 4: 19, 8: 15, 16: 12}[n.duration] for n in bar.notes))

    def _draw_bar(self, svg: SVG, bar: Bar, x: float, width: float, staff_top: float) -> None:
        s = self.style
        ink = s.ink
        staff_bottom = staff_top + 4 * s.staff_gap
        content_x = x + 8
        content_width = width - 16
        total_units = sum(16 / n.duration for n in bar.notes) or 1
        positions: list[tuple[Note, float]] = []
        cursor = content_x
        for note in bar.notes:
            note_width = content_width * (16 / note.duration) / total_units
            positions.append((note, cursor + note_width / 2))
            cursor += note_width

        beam_directions = self._beam_directions(positions)
        beam_ends = self._beam_ends(positions, staff_top, beam_directions)
        self._draw_beams(svg, positions, staff_top, beam_directions)
        for note, note_x in positions:
            self._draw_note(
                svg,
                note,
                note_x,
                staff_top,
                stem_up=beam_directions.get(note_x),
                stem_end=beam_ends.get(note_x),
            )

        boundary_x = x + width
        if bar.repeat_start:
            svg.line(x + 4, staff_top, x + 4, staff_bottom, stroke=ink, stroke_width=2.2)
            svg.line(x + 8, staff_top, x + 8, staff_bottom, stroke=ink, stroke_width=s.bar_width)
            for dot_y in (staff_top + 1.5 * s.staff_gap, staff_top + 2.5 * s.staff_gap):
                svg.ellipse(x + 12, dot_y, 1.7, 1.7, fill=ink)
        if bar.repeat_end:
            svg.line(boundary_x - 7, staff_top, boundary_x - 7, staff_bottom, stroke=ink, stroke_width=s.bar_width)
            svg.line(boundary_x - 3, staff_top, boundary_x - 3, staff_bottom, stroke=ink, stroke_width=2.2)
            for dot_y in (staff_top + 1.5 * s.staff_gap, staff_top + 2.5 * s.staff_gap):
                svg.ellipse(boundary_x - 12, dot_y, 1.7, 1.7, fill=ink)
        else:
            svg.line(boundary_x, staff_top, boundary_x, staff_bottom, stroke=ink,
                     stroke_width=2.0 if bar.final else s.bar_width)
        if bar.rehearsal:
            svg.text(boundary_x - width / 2, staff_bottom + 26, bar.rehearsal, fill=ink,
                     text_anchor="middle", font_family="Georgia, Times New Roman, serif", font_size=13)

    def _draw_note(self, svg: SVG, note: Note, x: float, staff_top: float,
                   stem_up: Optional[bool] = None,
                   stem_end: Optional[float] = None) -> None:
        s = self.style
        ink = s.ink
        middle = staff_top + 2 * s.staff_gap
        if note.rest:
            y = middle
            if note.duration == 4:
                svg.path(f"M {x-5:g} {y-2:g} q 3 -4 6 0 l -2 4 q -2 3 3 5", fill="none", stroke=ink, stroke_width=1.5)
            else:
                svg.rect(x - 5, y - 1.5, 10, 3, fill=ink)
            return

        y = middle - note.step * (s.staff_gap / 2)
        self._ledger_lines(svg, x, y, staff_top)
        accidental = note.display_accidental
        if accidental:
            symbol = "♯" if accidental == "#" else "♭" if accidental == "b" else "♮"
            svg.text(x - 12, y + 6, symbol, fill=ink,
                     font_family="Bravura, Noto Music, DejaVu Sans, serif", font_size=17)

        filled = note.duration not in (1, 2)
        svg.ellipse(x, y, s.note_width / 2, s.note_height / 2,
                    fill=ink if filled else "none", stroke=ink, stroke_width=1.1)
        if note.duration != 1:
            if stem_up is None:
                stem_up = note.step < 5
            stem_x = x + s.note_width / 2 if stem_up else x - s.note_width / 2
            stem_y = y - 3 if stem_up else y + 3
            if stem_end is None:
                stem_end = staff_top - 18 if stem_up else staff_top + 4 * s.staff_gap + 18
            svg.line(stem_x, stem_y, stem_x, stem_end, stroke=ink, stroke_width=s.stem, stroke_linecap="round")

    def _ledger_lines(self, svg: SVG, x: float, y: float, staff_top: float) -> None:
        s = self.style
        ink = s.ink
        if y < staff_top - 1:
            first = int((staff_top - y + s.staff_gap / 2) // s.staff_gap)
            for index in range(first, 0, -1):
                yy = staff_top - index * s.staff_gap
                if yy >= y - s.staff_gap / 2:
                    svg.line(x - 7, yy, x + 7, yy, stroke=ink, stroke_width=s.staff_width)
        elif y > staff_top + 4 * s.staff_gap + 1:
            distance = y - (staff_top + 4 * s.staff_gap)
            first = int((distance + s.staff_gap / 2) // s.staff_gap)
            for index in range(1, first + 1):
                yy = staff_top + 4 * s.staff_gap + index * s.staff_gap
                if yy <= y + s.staff_gap / 2:
                    svg.line(x - 7, yy, x + 7, yy, stroke=ink, stroke_width=s.staff_width)

    def _beam_directions(self, positions: Sequence[tuple[Note, float]]) -> dict[float, bool]:
        """Choose one stem direction for every beamed group.

        A beam is shared by a group, so its stems must all point toward the
        same side.  The average staff position is a compact approximation of
        the conventional engraving rule: notes mostly below the middle line
        stem up, notes mostly above it stem down.
        """
        directions: dict[float, bool] = {}
        group: list[tuple[Note, float]] = []
        for note, x in positions + [(Note("B4", 4), float("nan"))]:
            if note.duration in (8, 16) and not note.rest:
                group.append((note, x))
            elif group:
                if len(group) >= 2:
                    stem_up = sum(note.step for note, _ in group) / len(group) < 4.5
                    for _, note_x in group:
                        directions[note_x] = stem_up
                group = []
        return directions

    def _beam_ends(
        self,
        positions: Sequence[tuple[Note, float]],
        staff_top: float,
        beam_directions: dict[float, bool],
    ) -> dict[float, float]:
        """Return each beamed stem's endpoint on the sloped beam line."""
        ends: dict[float, float] = {}
        group: list[tuple[Note, float]] = []
        for note, x in positions + [(Note("B4", 4), float("nan"))]:
            if note.duration in (8, 16) and not note.rest:
                group.append((note, x))
            elif group:
                if len(group) >= 2:
                    stem_up = beam_directions[group[0][1]]
                    beam_y1, beam_y2 = self._beam_line(group, staff_top, stem_up)
                    for index, (_, note_x) in enumerate(group):
                        fraction = index / (len(group) - 1)
                        ends[note_x] = beam_y1 + (beam_y2 - beam_y1) * fraction
                group = []
        return ends

    def _beam_line(
        self,
        group: Sequence[tuple[Note, float]],
        staff_top: float,
        stem_up: bool,
    ) -> tuple[float, float]:
        """Choose a restrained engraved slope from the first/last notes."""
        s = self.style
        base = staff_top - 18 if stem_up else staff_top + 4 * s.staff_gap + 18
        first_y = staff_top + 2 * s.staff_gap - group[0][0].step * (s.staff_gap / 2)
        last_y = staff_top + 2 * s.staff_gap - group[-1][0].step * (s.staff_gap / 2)
        slope = max(-24.0, min(24.0, (last_y - first_y) * 0.35))
        return base - slope / 2, base + slope / 2

    def _draw_beams(self, svg: SVG, positions: Sequence[tuple[Note, float]], staff_top: float,
                    beam_directions: dict[float, bool]) -> None:
        s = self.style
        ink = s.ink
        group: list[tuple[Note, float]] = []
        for note, x in positions + [(Note("B4", 4), float("nan"))]:
            if note.duration in (8, 16) and not note.rest:
                group.append((note, x))
            elif group:
                if len(group) >= 2:
                    self._beam_group(svg, group, staff_top, beam_directions[group[0][1]])
                group = []

    def _beam_group(self, svg: SVG, group: Sequence[tuple[Note, float]], staff_top: float,
                    stem_up: bool) -> None:
        s = self.style
        ink = s.ink
        beam_y1, beam_y2 = self._beam_line(group, staff_top, stem_up)
        x1 = group[0][1] + s.note_width / 2 if stem_up else group[0][1] - s.note_width / 2
        x2 = group[-1][1] + s.note_width / 2 if stem_up else group[-1][1] - s.note_width / 2
        thickness = 4.0 if group[0][0].duration == 8 else 7.0
        underside1 = beam_y1 + thickness if stem_up else beam_y1 - thickness
        underside2 = beam_y2 + thickness if stem_up else beam_y2 - thickness
        svg.path(
            f"M {x1:g} {beam_y1:g} L {x2:g} {beam_y2:g} "
            f"L {x2:g} {underside2:g} L {x1:g} {underside1:g} Z",
            fill=ink,
        )


def make_demo_score() -> Score:
    """Return a compact example with the visual vocabulary of the reference."""
    def n(*values: str) -> list[Note]:
        return [Note(value[:-2], int(value[-1])) for value in values]

    systems = [
        System([
            Bar(n("G4:8", "A4:8", "B4:8", "D5:8", "C5:8", "B4:8")),
            Bar(n("A4:8", "B4:8", "C5:8", "D5:8", "C5:8", "B4:8")),
            Bar(n("A4:8", "G4:8", "F#4:8", "G4:8", "A4:8", "B4:8"), final=True),
        ], number="1."),
        System([
            Bar(n("D5:8", "C5:8", "B4:8", "A4:8", "G4:8", "F#4:8")),
            Bar(n("G4:8", "A4:8", "B4:8", "D5:8", "C5:8", "B4:8"), rehearsal="Fine."),
            Bar(n("A4:4", "G4:4", "F#4:4"), final=True),
        ]),
        System([
            Bar(n("G4:8", "B4:8", "D5:8", "G5:8", "F#5:8", "D5:8")),
            Bar(n("C5:8", "B4:8", "A4:8", "G4:8", "F#4:8", "G4:8")),
            Bar(n("A4:8", "B4:8", "C5:8", "D5:8", "E5:8", "F#5:8"), final=True),
        ]),
    ]
    return Score(systems, title="Tunes adapted to the French Slow Waltz.",
                 subtitle="A small SVG engraving example", footer="Engraved with Python and SVG")


if __name__ == "__main__":
    make_demo_score().write_svg("score.svg")
    print("wrote score.svg")
