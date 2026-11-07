"""Turn raw ATS job descriptions into clean, structured text.

Greenhouse (most of our sources) delivers HTML that is itself HTML-escaped
(`&lt;h2&gt;About the Role&lt;/h2&gt;`), and other sources deliver raw HTML.
Every downstream signal -- years-of-experience parsing, skill extraction,
embeddings -- needs plain text with real line structure, so it is cleaned once
here.
"""

import html
import re
from dataclasses import dataclass


_REAL_TAG = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")
_BR = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
_LI_OPEN = re.compile(r"<\s*li\b[^>]*>", re.IGNORECASE)
_BLOCK_CLOSE = re.compile(
    r"<\s*/\s*(?:p|div|li|ul|ol|h[1-6]|tr|table|section|blockquote)\s*>",
    re.IGNORECASE,
)


def clean_description(raw: str | None) -> str:
    """Return plain text with one logical line per paragraph/bullet/heading."""
    if not raw:
        return ""

    text = raw
    # Escaped HTML can be double-escaped; unescape until stable.
    for _ in range(3):
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped

    text = _BR.sub("\n", text)
    text = _LI_OPEN.sub("\n- ", text)
    text = _BLOCK_CLOSE.sub("\n", text)
    text = _REAL_TAG.sub(" ", text)

    text = (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )

    lines = []
    for line in text.splitlines():
        line = re.sub(r"[ \t ​ ]+", " ", line).strip()
        if line:
            lines.append(line)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------

# Order matters: "Preferred qualifications" must classify as preferred before
# the generic "qualifications" pattern is tried.
_HEADING_KINDS: list[tuple[str, re.Pattern[str]]] = [
    (
        "preferred",
        re.compile(
            r"^(?:preferred|nice[\s-]to[\s-]have|bonus|extra credit|pluses|"
            r"a plus|even better|ideally|what sets you apart|stand out|"
            r"it'?s a plus|desired|desirable|preferred skills)",
            re.IGNORECASE,
        ),
    ),
    (
        "requirements",
        re.compile(
            r"^(?:requirements?|(?:minimum|basic|required)?\s*qualifications?|"
            r"what you'?ll need|what we'?re looking for|what you bring|"
            r"about you|who you are|you have|your background|must[\s-]have|"
            r"skills|your experience|you might thrive|you may be a good fit|"
            r"minimum|what you should have|the ideal candidate|you are|"
            r"what we look for|what you need|what you bring|your expertise|"
            r"required skills|skills and experience|you will need|key skills|"
            r"you(?:'ll| will) thrive|thrive in this role|you(?:'ll| will) be a great fit|"
            r"you would be a great fit|you might be a good fit|good fit if|great fit if|"
            r"experience required|ideal profile|experience)",
            re.IGNORECASE,
        ),
    ),
    (
        "responsibilities",
        re.compile(
            r"^(?:responsibilit|what you'?ll do|what you will do|the role|"
            r"about the role|about this role|in this role|your impact|"
            r"your role|day[\s-]to[\s-]day|key duties|what the job|"
            r"the opportunity|the job|you will|you'?ll|what you'?ll be doing|"
            r"key job responsibilities|the impact you will have|"
            r"an overview of this role|a day in the life|a typical day|"
            r"the difference you will make|your mission|what you'?ll own)",
            re.IGNORECASE,
        ),
    ),
    (
        "benefits",
        re.compile(
            r"^(?:benefits|perks|compensation|salary|pay range|"
            r"what we offer|total rewards|equity|why you'?ll love|"
            r"our benefits|base pay|pay transparency|.*pay range|zone \d|"
            r"time off|health|financial benefits|how we'?ll take care|relocation)",
            re.IGNORECASE,
        ),
    ),
    (
        "legal",
        re.compile(
            r"^(?:equal opportunity|eeo|diversity|accommodation|privacy|"
            r"e-verify|export control|background check|notice|disclaimer|"
            r"our commitment to|compliance|equal)",
            re.IGNORECASE,
        ),
    ),
    (
        "about",
        re.compile(
            r"^(?:about (?:us|the company|the team)|who we are|our mission|"
            r"company overview|why join|life at|our story|about [A-Z])",
            re.IGNORECASE,
        ),
    ),
]


@dataclass
class Section:
    kind: str
    heading: str
    text: str


def _classify_heading(line: str) -> str | None:
    stripped = line.strip().strip("*_:#").strip()
    if not stripped or len(stripped) > 80 or stripped.startswith("-"):
        return None

    head, _, _ = stripped.partition(":")
    head = head.strip()
    if len(head.split()) > 9 or head.endswith("."):
        return None

    for kind, pattern in _HEADING_KINDS:
        if pattern.search(head):
            return kind
    return None


def split_sections(clean_text: str) -> list[Section]:
    """Split cleaned text into labelled sections using heading heuristics."""
    sections: list[Section] = []
    current = Section(kind="intro", heading="", text="")
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            current.text = "\n".join(buffer)
            sections.append(Section(current.kind, current.heading, current.text))
            buffer.clear()

    for line in clean_text.splitlines():
        kind = _classify_heading(line)
        if kind is not None:
            flush()
            current = Section(kind=kind, heading=line.strip(), text="")
            # "Requirements: 3+ years ..." keeps the trailing text.
            _, colon, trailing = line.partition(":")
            if colon and trailing.strip():
                buffer.append(trailing.strip())
        else:
            buffer.append(line)

    flush()
    return sections


def role_text(title: str, clean_text: str, max_chars: int = 2400) -> str:
    """Focused text describing the *role* (not the company), for embeddings.

    Company boilerplate, benefits, and legal text dominate the start and end of
    most postings; the first 256 tokens an embedding model reads should be about
    the job, so only responsibilities/requirements are kept when identifiable.
    """
    sections = split_sections(clean_text)
    keep = [
        section.text
        for section in sections
        if section.kind in {"responsibilities", "requirements", "preferred"}
    ]

    if not keep:
        keep = [
            section.text
            for section in sections
            if section.kind not in {"about", "benefits", "legal"}
        ]

    body = "\n".join(keep) or clean_text
    return f"{title}\n{body}"[:max_chars]
