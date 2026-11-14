"""Read source files and pair the forms that clear the similarity threshold."""

from __future__ import annotations

from pathlib import Path

from dryer.discover import language_of
from dryer.extract import entries_in_source
from dryer.model import Duplicate, Entry, Span
from dryer.shape import jaccard


def display_path(path: Path, root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _keep(entry: Entry, min_lines: int, min_nodes: int) -> bool:
    lines = entry.end_line - entry.start_line + 1
    return lines >= min_lines and entry.nodes >= min_nodes


def scan_files(
    files: list[Path], root: Path, min_lines: int, min_nodes: int
) -> tuple[list[Entry], list[str]]:
    entries: list[Entry] = []
    warnings: list[str] = []
    for path in files:
        language = language_of(path)
        if language is None:
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        file = display_path(path, root)
        found, warning = entries_in_source(language, source, path.as_posix(), file)
        if warning:
            warnings.append(f"{file}:{warning}")
        entries.extend(entry for entry in found if _keep(entry, min_lines, min_nodes))
    return entries, warnings


def _same_span(left: Entry, right: Entry) -> bool:
    if left.file != right.file:
        return False
    if left.start_line != right.start_line:
        return False
    return left.end_line == right.end_line


def _duplicate_key(item: Duplicate):
    score = -item.score
    return (
        score,
        item.language,
        item.left.file,
        item.left.start_line,
        item.right.file,
        item.right.start_line,
    )


def _identical_groups(group: list[Entry]) -> list[Duplicate]:
    """One candidate per set of two or more forms with the same fingerprints."""

    classes: dict[frozenset[str], list[Entry]] = {}
    for entry in group:
        if not entry.fingerprints:
            continue
        members = classes.setdefault(entry.fingerprints, [])
        if not any(_same_span(entry, seen) for seen in members):
            members.append(entry)
    return [
        Duplicate(
            score=1.0,
            language=first.language,
            left=Span(first.file, first.start_line, first.end_line),
            right=Span(second.file, second.start_line, second.end_line),
            left_nodes=first.nodes,
            right_nodes=second.nodes,
            others=tuple(Span(e.file, e.start_line, e.end_line) for e in rest),
        )
        for (first, second, *rest) in (m for m in classes.values() if len(m) > 1)
    ]


def find_duplicates(
    entries: list[Entry], threshold: float, group_identical: bool = False
) -> list[Duplicate]:
    """Pair forms of the same language. Each unordered pair is reported once.

    With `group_identical`, forms whose fingerprints are all the same are reported
    once as a group instead of as every pair among them.
    """

    by_language: dict[str, list[Entry]] = {}
    for entry in entries:
        by_language.setdefault(entry.language, []).append(entry)

    found: list[Duplicate] = []
    for language, group in by_language.items():
        for index, left in enumerate(group):
            for right in group[index + 1 :]:
                if _same_span(left, right):
                    continue
                score = jaccard(left.fingerprints, right.fingerprints)
                if score < threshold or (group_identical and score == 1.0):
                    continue
                found.append(
                    Duplicate(
                        score=score,
                        language=language,
                        left=Span(left.file, left.start_line, left.end_line),
                        right=Span(right.file, right.start_line, right.end_line),
                        left_nodes=left.nodes,
                        right_nodes=right.nodes,
                    )
                )
        if group_identical and threshold <= 1.0:
            found.extend(_identical_groups(group))
    found.sort(key=_duplicate_key)
    return found
