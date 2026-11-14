"""Text and EDN reports. The text layout matches dry4clj."""

from __future__ import annotations

from pathlib import Path

from dryer.model import Duplicate


def format_text(candidates: list[Duplicate]) -> str:
    if not candidates:
        return "No duplicate candidates found.\n"
    blocks = []
    for candidate in candidates:
        left = candidate.left
        right = candidate.right
        spans = [left, right, *candidate.others]
        copies = f" copies={len(spans)}" if candidate.others else ""
        lines = [f"  {span.file}:{span.start_line}-{span.end_line}" for span in spans]
        blocks.append("\n".join([f"DUPLICATE score={candidate.score:.2f}{copies}", *lines]))
    return "\n\n".join(blocks) + "\n"


def _edn_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _edn_float(value: float) -> str:
    text = f"{value:.12f}".rstrip("0").rstrip(".")
    if "." not in text:
        text += ".0"
    return text


def _span_edn(span) -> str:
    return (
        f"{{:file {_edn_string(span.file)}, "
        f":start-line {span.start_line}, :end-line {span.end_line}}}"
    )


def _others_edn(candidate: Duplicate) -> list[str]:
    if not candidate.others:
        return []
    return ["  :others [" + " ".join(_span_edn(span) for span in candidate.others) + "]"]


def _candidate_edn(candidate: Duplicate) -> str:
    return "\n".join(
        [
            f" {{:score {_edn_float(candidate.score)}",
            f"  :language {_edn_string(candidate.language)}",
            f"  :left {_span_edn(candidate.left)}",
            f"  :right {_span_edn(candidate.right)}",
            *_others_edn(candidate),
            f"  :left-nodes {candidate.left_nodes}",
            f"  :right-nodes {candidate.right_nodes}}}",
        ]
    )


def render_edn(candidates: list[Duplicate]) -> str:
    """EDN map `{:candidates [...]}` with dry4clj's keys, plus `:language`."""

    if not candidates:
        return "{:candidates []}\n"
    rows = [_candidate_edn(candidate) for candidate in candidates]
    return "{:candidates [\n" + "\n".join(rows) + "\n]}\n"


def metrics_path(root: Path) -> Path:
    return root / ".metrics" / "dry.edn"


def write_metrics(candidates: list[Duplicate], root: Path) -> Path:
    path = metrics_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_edn(candidates), encoding="utf-8")
    return path
