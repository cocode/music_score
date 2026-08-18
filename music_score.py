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

import base64
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
import re
from typing import Iterable, Optional, Sequence


PITCHES = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
NATURAL_STEPS = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
DIATONIC_FROM_C = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
NOTE_RE = re.compile(r"^([A-Ga-g])([#b♮]?)(-?\d+)$")


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
    beam_break_after: bool = False
    dots: int = 0

    def __post_init__(self) -> None:
        if self.duration not in (1, 2, 4, 8, 16):
            raise ValueError("duration must be one of 1, 2, 4, 8, or 16")
        if type(self.dots) is not int or self.dots < 0:
            raise ValueError("dots must be a non-negative integer")
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

    @property
    def rhythmic_units(self) -> float:
        """Duration in sixteenth-note units, including augmentation dots."""
        dot_factor = 2.0 - 2.0 ** (-self.dots)
        return (16 / self.duration) * dot_factor


@dataclass
class Bar:
    notes: Sequence[Note]
    repeat_start: bool = False
    repeat_end: bool = False
    repeat_both: bool = False
    repeat_dots: int = 2
    segno: bool = False
    segno_start: bool = False
    fermata: bool = False
    final: bool = False
    rehearsal: Optional[str] = None

    def __post_init__(self) -> None:
        self.notes = tuple(self.notes)
        if self.repeat_dots not in (2, 4):
            raise ValueError("repeat_dots must be 2 or 4")


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
    accidental_font_size: float = 27.0
    accidental_offset_x: float = 18.0
    accidental_spacing: float = 24.0
    beam_thickness: float = 4.0
    beam_clearance: float = 1.0
    minimum_intermediate_stem_ratio: float = 0.5
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


def _embedded_music_font() -> str:
    """Return an SVG font-face definition when the bundled Noto font exists."""
    font_path = Path(__file__).with_name("NotoMusic-Regular.ttf")
    try:
        encoded = base64.b64encode(font_path.read_bytes()).decode("ascii")
    except OSError:
        return ""
    return (
        "<defs><style>"
        '@font-face{font-family:"Noto Music";'
        f"src:url(data:font/ttf;base64,{encoded}) format(\"truetype\");"
        "font-weight:normal;font-style:normal;}"
        "</style></defs>"
    )


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
        embedded_font = _embedded_music_font()
        if embedded_font:
            svg.raw(embedded_font)
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
        svg.text(left + 7, staff_top + 4 * s.staff_gap, "𝄞", fill=ink,
                 font_family="Noto Music, Bravura, DejaVu Sans, serif", font_size=39.2)
        key_x = left + 41
        key_steps = (4, 1, 5, 2, 6, 3, 0)  # F, C, G, D, A, E, B in treble clef.
        for index, accidental in enumerate(self._key_accidentals(system.key)):
            symbol = "♯" if accidental == "#" else "♭"
            y = staff_top + 2 * s.staff_gap - key_steps[index] * (s.staff_gap / 2) + 6
            svg.text(key_x + index * 10, y, symbol, fill=ink,
                     font_family="DejaVu Sans, Georgia, serif", font_size=20)
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
        if system.bars and (system.bars[-1].repeat_end or system.bars[-1].repeat_start or system.bars[-1].repeat_both):
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

    def _bar_width(self, bar: Bar) -> float:
        # Width is intentionally generous, like a nineteenth-century plate:
        # short notes get grouped into visible beams instead of being cramped.
        note_widths = sum(
            {1: 30, 2: 25, 4: 19, 8: 15, 16: 12}[note.duration]
            * (2.0 - 2.0 ** (-note.dots))
            for note in bar.notes
        )
        accidental_space = sum(
            self.style.accidental_spacing
            for note in bar.notes
            if note.display_accidental
        )
        # Add accidental room after applying the minimum so a short measure
        # cannot absorb or discard the requested allowance.
        return max(68.0, 24.0 + note_widths) + accidental_space

    def _note_positions(
        self, bar: Bar, x: float, width: float
    ) -> list[tuple[Note, float]]:
        """Lay out notes rhythmically, reserving leading room for accidentals."""
        s = self.style
        content_x = x + 8
        content_width = width - 16
        total_units = sum(note.rhythmic_units for note in bar.notes) or 1
        accidental_space = sum(
            s.accidental_spacing for note in bar.notes if note.display_accidental
        )
        rhythmic_width = max(1.0, content_width - accidental_space)

        positions: list[tuple[Note, float]] = []
        cursor = content_x
        for note in bar.notes:
            if note.display_accidental:
                cursor += s.accidental_spacing
            note_width = rhythmic_width * note.rhythmic_units / total_units
            positions.append((note, cursor + note_width / 2))
            cursor += note_width
        return positions

    def _draw_bar(self, svg: SVG, bar: Bar, x: float, width: float, staff_top: float,
                  is_last: bool = False) -> None:
        s = self.style
        ink = s.ink
        staff_bottom = staff_top + 4 * s.staff_gap
        positions = self._note_positions(bar, x, width)

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
        repeat_dot_offsets = (
            (0.5, 1.5, 2.5, 3.5)
            if bar.repeat_dots == 4
            else (1.5, 2.5)
        )
        repeat_start_dot_x: Optional[float] = None
        if bar.repeat_both:
            repeat_x = boundary_x if is_last else x
            if is_last:
                first_bar_x, second_bar_x = repeat_x - 8, repeat_x - 4
                left_dot_x, right_dot_x = repeat_x - 12, repeat_x + 2
            else:
                first_bar_x, second_bar_x = repeat_x + 4, repeat_x + 8
                left_dot_x, right_dot_x = repeat_x, repeat_x + 12
            svg.line(first_bar_x, staff_top, first_bar_x, staff_bottom, stroke=ink, stroke_width=s.bar_width)
            svg.line(second_bar_x, staff_top, second_bar_x, staff_bottom, stroke=ink, stroke_width=2.2)
            for offset in repeat_dot_offsets:
                dot_y = staff_top + offset * s.staff_gap
                svg.ellipse(left_dot_x, dot_y, 1.7, 1.7, fill=ink)
                svg.ellipse(right_dot_x, dot_y, 1.7, 1.7, fill=ink)
        elif bar.repeat_start:
            if bar.repeat_dots == 4:
                # The historical four-dot form encloses the dot column
                # between two strokes. At an internal boundary, the left
                # stroke coincides with the preceding measure's barline.
                if is_last:
                    first_bar_x, dot_x, second_bar_x = (
                        boundary_x - 8, boundary_x - 4, boundary_x
                    )
                else:
                    first_bar_x, dot_x, second_bar_x = x, x + 4, x + 8
            elif is_last:
                repeat_x = boundary_x
                first_bar_x, second_bar_x, dot_x = repeat_x - 8, repeat_x - 4, repeat_x + 2
            else:
                # Reuse the shared measure boundary as the first stroke so a
                # normal start repeat has two visible strokes, not three.
                first_bar_x, second_bar_x, dot_x = x, x + 4, x + 8
            repeat_start_dot_x = dot_x
            svg.line(first_bar_x, staff_top, first_bar_x, staff_bottom, stroke=ink, stroke_width=s.bar_width)
            svg.line(second_bar_x, staff_top, second_bar_x, staff_bottom, stroke=ink, stroke_width=2.2)
            for offset in repeat_dot_offsets:
                dot_y = staff_top + offset * s.staff_gap
                svg.ellipse(dot_x, dot_y, 1.7, 1.7, fill=ink)
        if bar.repeat_end:
            svg.line(boundary_x - 7, staff_top, boundary_x - 7, staff_bottom, stroke=ink, stroke_width=s.bar_width)
            svg.line(boundary_x - 3, staff_top, boundary_x - 3, staff_bottom, stroke=ink, stroke_width=2.2)
            for offset in repeat_dot_offsets:
                dot_y = staff_top + offset * s.staff_gap
                svg.ellipse(boundary_x - 12, dot_y, 1.7, 1.7, fill=ink)
        elif not (bar.repeat_both or (bar.repeat_start and is_last)):
            svg.line(boundary_x, staff_top, boundary_x, staff_bottom, stroke=ink,
                     stroke_width=2.0 if bar.final else s.bar_width)
        if bar.rehearsal:
            svg.text(boundary_x - width / 2, staff_bottom + 26, bar.rehearsal, fill=ink,
                     text_anchor="middle", font_family="Georgia, Times New Roman, serif", font_size=13)
        if bar.segno:
            self._draw_segno(svg, boundary_x - 7, staff_top - 17)
        if bar.segno_start:
            segno_x = repeat_start_dot_x if repeat_start_dot_x is not None else x + 18
            self._draw_segno(svg, segno_x, staff_top - 17)
        if bar.fermata:
            fermata_x = boundary_x
            svg.path(
                f"M {fermata_x - 9:g} {staff_top - 17:g} Q {fermata_x:g} {staff_top - 26:g} {fermata_x + 9:g} {staff_top - 17:g}",
                fill="none", stroke=ink, stroke_width=1.5, stroke_linecap="round",
            )
            svg.ellipse(fermata_x, staff_top - 13, 2.0, 2.0, fill=ink)

    def _draw_segno(self, svg: SVG, x: float, y: float) -> None:
        """Draw the Unicode segno using Noto Music."""
        svg.text(x, y + 12, "𝄋", fill=self.style.ink,
                 font_family="Noto Music, Bravura, DejaVu Sans, serif", font_size=30,
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
            svg.text(x - s.accidental_offset_x, y + 8, symbol, fill=ink,
                     font_family="DejaVu Sans, Georgia, serif",
                     font_size=s.accidental_font_size, text_anchor="middle")

        filled = note.duration not in (1, 2)
        svg.ellipse(x, y, s.note_width / 2, s.note_height / 2,
                    fill=ink if filled else "none", stroke=ink, stroke_width=1.1)
        if note.dots:
            # A dot following a line note is conventionally moved into the
            # space above so it cannot disappear into the staff line.
            dot_y = y - s.staff_gap / 2 if note.step % 2 == 0 else y
            first_dot_x = x + s.note_width / 2 + 4.0
            for dot_index in range(note.dots):
                svg.ellipse(first_dot_x + dot_index * 5.0, dot_y, 1.45, 1.45,
                            fill=ink)
        if note.duration != 1:
            if stem_up is None:
                stem_up = note.step < 0.5
            stem_x = x + s.note_width / 2 if stem_up else x - s.note_width / 2
            stem_y = y
            is_beamed = stem_end is not None
            if stem_end is None:
                stem_end = self._default_stem_end(y, stem_up)
            svg.line(stem_x, stem_y, stem_x, stem_end, stroke=ink, stroke_width=s.stem,
                     stroke_linecap="butt" if is_beamed else "round")
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
                    f"M {stem_x:g} {y:g} q 7 -2 10 -7 q -5 2 -10 2 Z",
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
        staff_bottom = staff_top + 4 * s.staff_gap
        if y < staff_top - 1:
            # Work outward from the staff and stop at the note. This draws a
            # ledger line through a note on a line, but never beyond it.
            yy = staff_top - s.staff_gap
            while yy >= y:
                svg.line(x - 8.75, yy, x + 8.75, yy,
                         stroke=ink, stroke_width=s.staff_width)
                yy -= s.staff_gap
        elif y > staff_bottom + 1:
            yy = staff_bottom + s.staff_gap
            while yy <= y:
                svg.line(x - 8.75, yy, x + 8.75, yy,
                         stroke=ink, stroke_width=s.staff_width)
                yy += s.staff_gap

    @staticmethod
    def _beam_groups(
        positions: Sequence[tuple[Note, float]],
    ) -> list[tuple[tuple[Note, float], ...]]:
        """Split consecutive short notes at rests and explicit beam breaks."""
        groups: list[tuple[tuple[Note, float], ...]] = []
        group: list[tuple[Note, float]] = []
        for note, x in positions:
            if note.duration in (8, 16) and not note.rest:
                group.append((note, x))
                if note.beam_break_after:
                    groups.append(tuple(group))
                    group = []
            elif group:
                groups.append(tuple(group))
                group = []
        if group:
            groups.append(tuple(group))
        return groups

    def _beam_directions(self, positions: Sequence[tuple[Note, float]]) -> dict[float, bool]:
        """Choose one stem direction for every beamed group.

        A beam is shared by a group, so its stems must all point toward the
        same side.  The average staff position is a compact approximation of
        the conventional engraving rule: notes mostly below the middle line
        stem up, notes mostly above it stem down.
        """
        directions: dict[float, bool] = {}
        for group in self._beam_groups(positions):
            if len(group) >= 2:
                stem_up = sum(note.step for note, _ in group) / len(group) < 0.5
                for _, note_x in group:
                    directions[note_x] = stem_up
        return directions

    def _beam_ends(
        self,
        positions: Sequence[tuple[Note, float]],
        staff_top: float,
        beam_directions: dict[float, bool],
    ) -> dict[float, float]:
        """Return each beamed stem's endpoint on the sloped beam line."""
        ends: dict[float, float] = {}
        for group in self._beam_groups(positions):
            if len(group) >= 2:
                stem_up = beam_directions[group[0][1]]
                beam_y1, beam_y2 = self._beam_line(group, staff_top, stem_up)
                first_x = self._stem_x(group[0], stem_up)
                last_x = self._stem_x(group[-1], stem_up)
                for item in group:
                    note_x = item[1]
                    stem_x = self._stem_x(item, stem_up)
                    ends[note_x] = self._line_y(
                        stem_x, first_x, beam_y1, last_x, beam_y2
                    )
        return ends

    def _beam_line(
        self,
        group: Sequence[tuple[Note, float]],
        staff_top: float,
        stem_up: bool,
    ) -> tuple[float, float]:
        """Find a beam line that clears every notehead in the group.

        The first and last stems begin at their normal lengths. If that line
        would cross a middle notehead, one or both endpoint stems are extended
        away from the notes by the smallest incremental correction needed.
        The same adjustment also prevents any interior stem from becoming
        shorter than the configured fraction of a normal stem.
        """
        s = self.style
        first_y = self._note_y(group[0][0], staff_top)
        last_y = self._note_y(group[-1][0], staff_top)
        first_end = self._default_stem_end(first_y, stem_up)
        last_end = self._default_stem_end(last_y, stem_up)
        first_x = self._stem_x(group[0], stem_up)
        last_x = self._stem_x(group[-1], stem_up)
        outward = -1.0 if stem_up else 1.0
        first_extension = 0.0
        last_extension = 0.0

        # Test the full rectangular envelope of each oval notehead. Using its
        # left, center, and right x positions keeps a steep beam from clipping
        # an edge even when it clears the center of the ellipse.
        for note_index, (note, note_x) in enumerate(group):
            note_y = self._note_y(note, staff_top)
            sample_left = max(first_x, note_x - s.note_width / 2)
            sample_right = min(last_x, note_x + s.note_width / 2)
            if sample_left > sample_right:
                continue
            sample_center = min(max(note_x, sample_left), sample_right)
            for sample_x in (sample_left, sample_center, sample_right):
                fraction = (sample_x - first_x) / (last_x - first_x)
                first_weight = 1.0 - fraction
                last_weight = fraction
                base_y = first_end + (last_end - first_end) * fraction
                extension = (
                    first_weight * first_extension
                    + last_weight * last_extension
                )
                beam_y = base_y + outward * extension

                if stem_up:
                    beam_near_edge = beam_y + s.beam_thickness
                    allowed_edge = note_y - s.note_height / 2 - s.beam_clearance
                    deficit = beam_near_edge - allowed_edge
                else:
                    beam_near_edge = beam_y - s.beam_thickness
                    allowed_edge = note_y + s.note_height / 2 + s.beam_clearance
                    deficit = allowed_edge - beam_near_edge

                if deficit > 0:
                    # Project the correction onto the two endpoint stems in
                    # proportion to how much each endpoint controls this x.
                    denominator = first_weight ** 2 + last_weight ** 2
                    first_extension += deficit * first_weight / denominator
                    last_extension += deficit * last_weight / denominator

            if 0 < note_index < len(group) - 1:
                # Measure the interior stem at its actual attachment point,
                # then lengthen the endpoint stems if interpolation would
                # make it less than half the ordinary stem length.
                stem_x = self._stem_x((note, note_x), stem_up)
                fraction = (stem_x - first_x) / (last_x - first_x)
                first_weight = 1.0 - fraction
                last_weight = fraction
                base_y = first_end + (last_end - first_end) * fraction
                extension = (
                    first_weight * first_extension
                    + last_weight * last_extension
                )
                beam_y = base_y + outward * extension
                stem_length = outward * (beam_y - note_y)
                normal_stem_length = 3.5 * s.staff_gap
                minimum_stem_length = (
                    normal_stem_length * s.minimum_intermediate_stem_ratio
                )
                deficit = minimum_stem_length - stem_length
                if deficit > 0:
                    denominator = first_weight ** 2 + last_weight ** 2
                    first_extension += deficit * first_weight / denominator
                    last_extension += deficit * last_weight / denominator

        return (
            first_end + outward * first_extension,
            last_end + outward * last_extension,
        )

    def _draw_beams(self, svg: SVG, positions: Sequence[tuple[Note, float]], staff_top: float,
                    beam_directions: dict[float, bool]) -> None:
        for group in self._beam_groups(positions):
            if len(group) >= 2:
                self._beam_group(svg, group, staff_top, beam_directions[group[0][1]])

    def _beam_group(self, svg: SVG, group: Sequence[tuple[Note, float]], staff_top: float,
                    stem_up: bool) -> None:
        s = self.style
        first_x, first_y, last_x, last_y = self._beam_geometry(
            group, staff_top, stem_up
        )
        self._draw_beam_segment(svg, first_x, first_y, last_x, last_y, stem_up)

        # Sixteenth-note groups carry a second parallel beam. A lone
        # sixteenth inside a beamed group gets a short secondary flag.
        secondary_shift = s.beam_thickness + 2.0
        if not stem_up:
            secondary_shift = -secondary_shift
        run: list[int] = []
        for index in range(len(group) + 1):
            if index < len(group) and group[index][0].duration == 16:
                run.append(index)
            elif run:
                if len(run) >= 2:
                    run_first_x = self._stem_x(group[run[0]], stem_up)
                    run_last_x = self._stem_x(group[run[-1]], stem_up)
                    run_first_y = self._line_y(
                        run_first_x, first_x, first_y, last_x, last_y
                    ) + secondary_shift
                    run_last_y = self._line_y(
                        run_last_x, first_x, first_y, last_x, last_y
                    ) + secondary_shift
                    self._draw_beam_segment(
                        svg,
                        run_first_x,
                        run_first_y,
                        run_last_x,
                        run_last_y,
                        stem_up,
                    )
                else:
                    self._draw_sixteenth_stub(
                        svg,
                        run[0],
                        group,
                        stem_up,
                        first_x,
                        first_y,
                        last_x,
                        last_y,
                        secondary_shift,
                    )
                run = []

    def _stem_x(self, item: tuple[Note, float], stem_up: bool) -> float:
        """Return the x coordinate where this note's stem meets its beams."""
        x = item[1]
        offset = self.style.note_width / 2
        return x + offset if stem_up else x - offset

    def _beam_geometry(
        self,
        group: Sequence[tuple[Note, float]],
        staff_top: float,
        stem_up: bool,
    ) -> tuple[float, float, float, float]:
        first_y, last_y = self._beam_line(group, staff_top, stem_up)
        return (
            self._stem_x(group[0], stem_up),
            first_y,
            self._stem_x(group[-1], stem_up),
            last_y,
        )

    @staticmethod
    def _line_y(x: float, x1: float, y1: float, x2: float, y2: float) -> float:
        """Interpolate y on a beam using actual horizontal stem positions."""
        if x1 == x2:
            return y1
        return y1 + (y2 - y1) * ((x - x1) / (x2 - x1))

    def _draw_beam_segment(
        self,
        svg: SVG,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        stem_up: bool,
    ) -> None:
        """Draw a constant-thickness beam with vertical ends."""
        s = self.style
        thickness = s.beam_thickness
        underside1 = y1 + thickness if stem_up else y1 - thickness
        underside2 = y2 + thickness if stem_up else y2 - thickness
        svg.path(
            f"M {x1:g} {y1:g} L {x2:g} {y2:g} "
            f"L {x2:g} {underside2:g} L {x1:g} {underside1:g} Z",
            fill=s.ink,
        )

    def _draw_sixteenth_stub(
        self,
        svg: SVG,
        index: int,
        group: Sequence[tuple[Note, float]],
        stem_up: bool,
        first_x: float,
        first_y: float,
        last_x: float,
        last_y: float,
        shift: float,
    ) -> None:
        """Draw a partial secondary beam toward the neighboring note."""
        stem_x = self._stem_x(group[index], stem_up)
        if index == 0:
            neighbor_x = self._stem_x(group[1], stem_up)
        elif index == len(group) - 1:
            neighbor_x = self._stem_x(group[index - 1], stem_up)
        else:
            left_x = self._stem_x(group[index - 1], stem_up)
            right_x = self._stem_x(group[index + 1], stem_up)
            neighbor_x = left_x if stem_x - left_x <= right_x - stem_x else right_x

        # Carry the secondary beam all the way to the neighboring stem. Both
        # endpoints are evaluated on the primary beam, keeping the two
        # strokes parallel and ensuring there is no gap at either stem.
        end_x = neighbor_x
        stem_y = self._line_y(stem_x, first_x, first_y, last_x, last_y) + shift
        end_y = self._line_y(end_x, first_x, first_y, last_x, last_y) + shift
        self._draw_beam_segment(
            svg, stem_x, stem_y, end_x, end_y, stem_up
        )


def make_demo_score() -> Score:
    """Load the external example score for backwards compatibility."""
    from render_score import score_from_file

    return score_from_file("example_score.json")


if __name__ == "__main__":
    make_demo_score().write_svg("score.svg")
    print("wrote score.svg")
