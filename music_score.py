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
        # B4 is the middle staff line. Keeping it at step zero makes the
        # pitch-to-staff mapping agree with the treble clef: E4 is -4, C5 is
        # +1, and F5 (the top line) is +4.
        return (octave - 4) * 7 + DIATONIC_FROM_C[letter] - 6

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
    segno: bool = False
    final: bool = False
    rehearsal: Optional[str] = None

    def __post_init__(self) -> None:
        self.notes = tuple(self.notes)


@dataclass
class System:
    bars: Sequence[Bar]
    number: Optional[str] = None
    no_label: bool = False
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
    note_width: float = 11.0
    note_height: float = 7.5
    beam_thickness: float = 4.0
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
            if system.no_label:
                svg.text(left - 44, staff_top + 11, "No", fill=ink,
                         font_family="Georgia, Times New Roman, serif", font_size=13,
                         font_weight="bold")
            svg.text(left - 44, staff_top + 29, system.number, fill=ink,
                     font_family="Georgia, Times New Roman, serif", font_size=19, font_weight="bold")
        if system.label:
            svg.text(left - 4, staff_top - 9, system.label, fill=ink,
                     font_family="Georgia, Times New Roman, serif", font_size=10, font_style="italic")

        # Unicode music symbols keep the library font-independent at the SVG
        # level while allowing a high-quality installed music font to be used.
        svg.text(left + 7, staff_top + 43, "𝄞", fill=ink,
                 font_family="Bravura, Noto Music, DejaVu Sans, serif", font_size=73.5)
        key_x = left + 41
        key_steps = (4, 1, 5, 2, 6, 3, 0)  # F, C, G, D, A, E, B in treble clef.
        for index, accidental in enumerate(self._key_accidentals(system.key)):
            symbol = "♯" if accidental == "#" else "♭"
            y = staff_top + 2 * s.staff_gap - key_steps[index] * (s.staff_gap / 2) + 6
            svg.text(key_x + index * 10, y, symbol, fill=ink,
                     font_family="Bravura, Noto Music, DejaVu Sans, serif", font_size=18)
        time_x = key_x + len(self._key_accidentals(system.key)) * 10 + 16
        if system.time:
            numerator, denominator = system.time.split("/", 1)
            svg.text(time_x, staff_top + 12, numerator, fill=ink, font_family="Georgia, serif", font_size=20, font_weight="bold")
            svg.text(time_x, staff_top + 36, denominator, fill=ink, font_family="Georgia, serif", font_size=20, font_weight="bold")

        content_left = time_x + 26
        content_right = right - 3
        bar_widths = [self._bar_width(bar) for bar in system.bars]
        scale = max(0.65, (content_right - content_left) / max(1, sum(bar_widths)))
        widths = [natural_width * scale for natural_width in bar_widths]
        staff_end = content_left + sum(widths)
        if system.bars and (system.bars[-1].repeat_end or system.bars[-1].repeat_start):
            # The outer stroke of a repeat-end sign is three units inside the
            # nominal bar boundary; staff lines stop at that stroke.
            staff_end -= 3
        for line_no in range(5):
            yy = staff_top + line_no * s.staff_gap
            svg.line(left, yy, staff_end, yy, stroke=ink, stroke_width=s.staff_width, stroke_linecap="round")
        x = content_left
        for index, (bar, width) in enumerate(zip(system.bars, widths)):
            self._draw_bar(svg, bar, x, width, staff_top, is_last=index == len(widths) - 1)
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

    def _draw_bar(self, svg: SVG, bar: Bar, x: float, width: float, staff_top: float,
                  is_last: bool = False) -> None:
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
        for note, note_x in positions:
            self._draw_note(
                svg,
                note,
                note_x,
                staff_top,
                stem_up=beam_directions.get(note_x),
                stem_end=beam_ends.get(note_x),
            )
        # Paint the beam over the stem ends so no stem cap protrudes through
        # the opposite side of the joining stroke.
        self._draw_beams(svg, positions, staff_top, beam_directions)

        boundary_x = x + width
        if bar.repeat_start:
            if is_last:
                repeat_x = boundary_x
                first_bar_x, second_bar_x, dot_x = repeat_x - 8, repeat_x - 4, repeat_x + 2
            else:
                first_bar_x, second_bar_x, dot_x = x + 4, x + 8, x + 12
            svg.line(first_bar_x, staff_top, first_bar_x, staff_bottom, stroke=ink, stroke_width=s.bar_width)
            svg.line(second_bar_x, staff_top, second_bar_x, staff_bottom, stroke=ink, stroke_width=2.2)
            for dot_y in (staff_top + 1.5 * s.staff_gap, staff_top + 2.5 * s.staff_gap):
                svg.ellipse(dot_x, dot_y, 1.7, 1.7, fill=ink)
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
        if bar.segno:
            svg.text(boundary_x - 7, staff_top - 17, "𝄋", fill=ink,
                     font_family="Bravura, Noto Music, DejaVu Sans, serif", font_size=25,
                     text_anchor="middle")

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

        y = self._note_y(note, staff_top)
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
                stem_up = note.step < 0.5
            stem_x = x + s.note_width / 2 if stem_up else x - s.note_width / 2
            stem_y = y
            is_beamed = stem_end is not None
            if stem_end is None:
                stem_end = self._default_stem_end(y, stem_up)
            svg.line(stem_x, stem_y, stem_x, stem_end, stroke=ink, stroke_width=s.stem, stroke_linecap="round")
            # A short note outside a beamed group still needs its flag. Notes
            # that received a beam endpoint are already connected by a beam.
            if note.duration in (8, 16) and not is_beamed:
                self._draw_flags(svg, stem_x, stem_end, stem_up, note.duration)

    def _draw_flags(self, svg: SVG, stem_x: float, stem_end: float,
                    stem_up: bool, duration: int) -> None:
        """Draw one eighth-note flag or two sixteenth-note flags."""
        ink = self.style.ink
        count = 1 if duration == 8 else 2
        for index in range(count):
            offset = index * 5.0
            if stem_up:
                y = stem_end + offset
                svg.path(
                    f"M {stem_x:g} {y:g} q 7 2 10 7 q -5 -2 -10 -2 Z",
                    fill=ink,
                )
            else:
                y = stem_end - offset
                svg.path(
                    f"M {stem_x:g} {y:g} q -7 -2 -10 -7 q 5 2 10 2 Z",
                    fill=ink,
                )

    def _note_y(self, note: Note, staff_top: float) -> float:
        return staff_top + 2 * self.style.staff_gap - note.step * (self.style.staff_gap / 2)

    def _default_stem_end(self, note_y: float, stem_up: bool) -> float:
        stem_start = note_y
        stem_length = 3.5 * self.style.staff_gap
        return stem_start - stem_length if stem_up else stem_start + stem_length

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
                    stem_up = sum(note.step for note, _ in group) / len(group) < 0.5
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
        """Connect the normal-length stems of the first and last notes.

        Interior stems are then interpolated onto this line. This is the
        usual engraved construction for a sloped beam: the endpoints retain
        their ordinary stem length, while only the middle stems are adjusted.
        """
        first_y = self._note_y(group[0][0], staff_top)
        last_y = self._note_y(group[-1][0], staff_top)
        return (
            self._default_stem_end(first_y, stem_up),
            self._default_stem_end(last_y, stem_up),
        )

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
        thickness = s.beam_thickness
        underside1 = beam_y1 + thickness if stem_up else beam_y1 - thickness
        underside2 = beam_y2 + thickness if stem_up else beam_y2 - thickness
        svg.path(
            f"M {x1:g} {beam_y1:g} L {x2:g} {beam_y2:g} "
            f"L {x2:g} {underside2:g} L {x1:g} {underside1:g} Z",
            fill=ink,
        )


def make_demo_score() -> Score:
    """Load the external example score for backwards compatibility."""
    from render_score import score_from_file

    return score_from_file("example_score.json")


if __name__ == "__main__":
    make_demo_score().write_svg("score.svg")
    print("wrote score.svg")
