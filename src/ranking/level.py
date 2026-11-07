"""Estimate how senior a posting is, and whether it fits an entry-level search.

Seniority is the single most important filter for a new-grad search, and it is
expressed in three different places, each unreliable on its own:

1. the title        -- "Senior", "Staff", "Engineer III", "Software Engineer 5"
2. the requirements -- "5+ years of professional experience"
3. the scope        -- "mentor engineers", "set technical direction"

Descriptions are never allowed to *override* a senior title: senior postings
routinely contain junior-sounding boilerplate (internship programs, "0-1 years
with Kubernetes"), which is exactly how senior roles used to slip through.
"""

import math
import re
from dataclasses import dataclass, field

from src.ranking.text_clean import split_sections


# Postings asking for more than this many years are not entry-level searches.
MAX_REQUIRED_YEARS = 3

_NUM_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "fifteen": 15,
}
_NUM = r"(?:\d{1,2}(?:\.\d)?|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen)"

_YEARS_RE = re.compile(
    rf"(?<![\w$.,])(?P<lo>{_NUM})\s*"
    rf"(?:\+|(?:-|to)\s*(?P<hi>{_NUM})\+?|\s+or\s+more)?\s*"
    r"(?:years?|yrs?)\b(?!\s*(?:old|of age|ago|in a row))",
    re.IGNORECASE,
)

_EXPERIENCE_CUE = re.compile(
    r"experience|background|expertise|proficien|professional|hands-on|industry|"
    r"track record|working (?:in|with|on)|building|developing|designing|"
    r"delivering|engineering|software|programming|coding|operating|shipping|"
    r"production|managing|leading",
    re.IGNORECASE,
)

# Phrases that make a "N years" mention about the *company*, not the candidate.
_HISTORY_CUE = re.compile(
    r"(?:founded|established|since|celebrat|anniversary|we(?:'ve| have) been|"
    r"has been|have been|over the (?:past|last)|in the (?:past|last)|"
    r"for the (?:past|last))\b",
    re.IGNORECASE,
)

# "ideally" is deliberately absent: "5+ years of backend, ideally in fintech"
# is a 5-year requirement whose *domain* is ideal, not the years.
_PREFERRED_CUE = re.compile(
    r"preferred|nice[\s-]to[\s-]have|bonus|a plus|desirable|"
    r"would be (?:great|nice)|extra credit",
    re.IGNORECASE,
)

# A preference expressed about a *different* skill in the same sentence
# ("... is a plus", "... highly desirable") must not demote the years phrase.
_CLAUSE_BREAK = re.compile(r";|\s[-–—]\s|,\s+(?:and|but|while|though)\s")

_REQUIRED_CUE = re.compile(r"\b(?:minimum|required|requires?|must|at least)\b", re.IGNORECASE)

_DEGREE_CUE = re.compile(
    r"degree|bachelor|master|ph\.?d|\bb\.?s\.?\b|\bm\.?s\.?\b", re.IGNORECASE
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _to_int(token: str) -> int:
    token = token.lower()
    if token in _NUM_WORDS:
        return _NUM_WORDS[token]
    return math.ceil(float(token))


@dataclass
class YearsRequirement:
    required: int | None = None
    preferred: int | None = None
    evidence: list[str] = field(default_factory=list)


def _clause_around(sentence: str, match: "re.Match[str]") -> str:
    start = 0
    for boundary in _CLAUSE_BREAK.finditer(sentence):
        if boundary.end() <= match.start():
            start = boundary.end()
        elif boundary.start() >= match.end():
            return sentence[start: boundary.start()]
    return sentence[start:]


_DOCTORAL = re.compile(r"ph\.?d|doctora", re.IGNORECASE)


def _non_doctoral_values(sentence: str) -> list[int]:
    values: list[int] = []
    for clause in re.split(r";|\bor\b", sentence, flags=re.IGNORECASE):
        if _DOCTORAL.search(clause):
            continue
        values.extend(_to_int(match.group("lo")) for match in _YEARS_RE.finditer(clause))
    return values


def extract_years_requirement(clean_text: str) -> YearsRequirement:
    """Find the candidate's *primary* years-of-experience requirement.

    The primary requirement is the largest REQUIRED mention (ranges use their
    lower bound, e.g. "3-5 years" -> 3). Mentions in preferred contexts are
    tracked separately and never count against the role. Using the largest
    rather than the smallest mention is deliberate: "5+ years of backend" plus
    "1+ year with Kubernetes" is a 5-year role.
    """
    result = YearsRequirement()

    for section in split_sections(clean_text):
        if section.kind in {"about", "benefits", "legal"}:
            continue

        for line in section.text.splitlines():
            for sentence in _SENTENCE_SPLIT.split(line):
                matches = list(_YEARS_RE.finditer(sentence))
                if not matches:
                    continue
                if not _EXPERIENCE_CUE.search(sentence):
                    continue

                found: list[tuple[int, re.Match[str]]] = []
                for match in matches:
                    if _HISTORY_CUE.search(sentence[max(0, match.start() - 80): match.start()]):
                        continue
                    found.append((_to_int(match.group("lo")), match))

                if not found:
                    continue

                values = [value for value, _ in found]

                # "BS + 8 years, or MS + 6 years, or PhD + 3 years": alternatives ->
                # the easiest path that does not need a doctorate.
                is_alternative = (
                    len(values) > 1
                    and _DEGREE_CUE.search(sentence)
                    and re.search(r"\bor\b|;", sentence, re.IGNORECASE)
                )
                if is_alternative:
                    value = min(_non_doctoral_values(sentence) or values)
                else:
                    value = max(values)

                anchor = next(
                    (match for found_value, match in found if found_value == value),
                    found[0][1],
                )
                clause = _clause_around(sentence, anchor)
                preferred = section.kind == "preferred" or (
                    bool(_PREFERRED_CUE.search(clause))
                    and not _REQUIRED_CUE.search(clause)
                )

                if preferred:
                    result.preferred = max(result.preferred or 0, value)
                else:
                    result.required = max(result.required or 0, value)
                    result.evidence.append(sentence.strip()[:160])

    return result


# ---------------------------------------------------------------------------
# Title signals
# ---------------------------------------------------------------------------

_SENIOR_TITLE = re.compile(
    r"\b(?:senior|sr\.?|staff|principal|lead|distinguished|fellow|architect|"
    r"manager|director|head of|vp|vice president|chief|president|svp|evp)\b",
    re.IGNORECASE,
)

_DOCTORATE_TITLE = re.compile(r"\bph\.?d\b", re.IGNORECASE)

_ROLE_NOUN = (
    r"(?:engineer|developer|scientist|analyst|sde|swe|programmer|specialist|"
    r"technician|researcher)"
)
_ROMAN_LEVEL = re.compile(rf"\b{_ROLE_NOUN}\s*[-,]?\s*(?P<lvl>i{{1,3}}|iv|vi?)\b", re.IGNORECASE)
_NUMERIC_LEVEL = re.compile(rf"\b{_ROLE_NOUN}\s*[-,]?\s*(?P<lvl>[1-9])\b(?!\s*[-+]\s*\d)", re.IGNORECASE)
_L_LEVEL = re.compile(r"\(?\bL(?P<lvl>[1-9])\b\)?")
_ROMAN_VALUES = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6}

_ENTRY_TITLE = re.compile(
    r"new[\s-]?grad(?:uate)?|recent grad|early[\s-]career|entry[\s-]level|"
    r"\bjunior\b|\bjr\.?\b|\bassociate\b|university grad|college grad|"
    r"\bgraduate\b|apprentice|rotational",
    re.IGNORECASE,
)

_ENTRY_DESCRIPTION = [
    re.compile(
        r"\bthis\s+(?:role|position|opportunity|job)\b.{0,120}"
        r"(?:new[\s-]?grad|recent grad|early[\s-]career|entry[\s-]level)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(r"(?:new|recent)\s+grad(?:uate)?s?\s+(?:are\s+)?(?:encouraged|welcome)", re.IGNORECASE),
    re.compile(
        r"(?:looking for|seeking|hiring)\b.{0,60}"
        r"(?:new[\s-]?grad|recent grad|early[\s-]career|entry[\s-]level)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(r"\b0\s*(?:-|to)\s*[12]\s*years?\b", re.IGNORECASE),
    re.compile(r"no\s+(?:prior|previous)\s+(?:professional\s+)?experience\s+(?:is\s+)?(?:required|necessary|needed)", re.IGNORECASE),
]

# Weak scope signals: senior responsibilities without an explicit title/years.
_SCOPE_SIGNALS = [
    re.compile(r"\bmentor(?:ing|s)?\s+(?:junior|other|less|fellow|engineers|team|and\s+(?:coach|grow))", re.IGNORECASE),
    re.compile(r"\blead(?:ing)?\s+(?:a\s+|the\s+)?(?:team|project|initiative|effort|technical)", re.IGNORECASE),
    re.compile(r"\btechnical\s+(?:leadership|direction|strategy|vision)", re.IGNORECASE),
    re.compile(r"\bset(?:ting)?\s+(?:the\s+)?(?:technical\s+)?(?:direction|vision|roadmap)", re.IGNORECASE),
    re.compile(r"\bown(?:ing)?\s+(?:the\s+)?(?:architecture|roadmap|technical)", re.IGNORECASE),
    re.compile(r"\b(?:proven\s+track\s+record|deep\s+expertise|extensive\s+experience|expert\s+in)\b", re.IGNORECASE),
]


@dataclass
class LevelAssessment:
    level: str = "unknown"          # entry | junior_mid | mid | senior | unknown
    gate: bool = False              # True -> exclude from an entry-level search
    gate_reason: str = ""
    level_score: float = 0.5        # 0..1 fit to an entry-level search
    years_required: int | None = None
    years_preferred: int | None = None
    entry_signals: list[str] = field(default_factory=list)
    senior_signals: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.entry_signals:
            return "Entry-level: " + ", ".join(self.entry_signals[:2])
        if self.gate:
            return self.gate_reason
        if self.years_required is not None:
            return f"Asks for {self.years_required}+ years"
        if self.years_preferred is not None and self.years_preferred >= 5:
            return f"Prefers {self.years_preferred}+ years"
        return "Level not stated"


def _without_generic_staff(title: str) -> str:
    """"Member of Technical Staff" is a generic engineer title at AI labs."""
    return re.sub(r"member of technical staff", "", title, flags=re.IGNORECASE)


def has_senior_title(title: str) -> bool:
    return bool(_SENIOR_TITLE.search(_without_generic_staff(title)))


def _title_level(title: str) -> tuple[str | None, str]:
    """Return (level, signal) from numerals/level codes in the title."""
    roman = _ROMAN_LEVEL.search(title)
    if roman:
        value = _ROMAN_VALUES[roman.group("lvl").lower()]
        return _numeral_level(value), f"title level {roman.group('lvl').upper()}"

    numeric = _NUMERIC_LEVEL.search(title)
    if numeric:
        value = int(numeric.group("lvl"))
        return _numeral_level(value), f"title level {value}"

    l_level = _L_LEVEL.search(title)
    if l_level:
        value = int(l_level.group("lvl"))
        # L1-L2 junior, L3 early-mid, L4+ mid/senior.
        if value <= 2:
            return "entry", f"title level L{value}"
        if value == 3:
            return "junior_mid", "title level L3"
        return "senior", f"title level L{value}"

    return None, ""


def _numeral_level(value: int) -> str:
    if value <= 1:
        return "entry"
    if value == 2:
        return "junior_mid"
    return "senior"


def assess_level(title: str, clean_text: str) -> LevelAssessment:
    """Classify a posting's level and decide whether it is entry-level-gated."""
    assessment = LevelAssessment()

    scrubbed_title = _without_generic_staff(title)

    years = extract_years_requirement(clean_text)
    assessment.years_required = years.required
    assessment.years_preferred = years.preferred

    # ---- hard senior signals (never overridden by the description) ----------
    senior_title = _SENIOR_TITLE.search(scrubbed_title)
    entry_title = _ENTRY_TITLE.search(scrubbed_title)
    numeral_level, numeral_signal = _title_level(scrubbed_title)

    if senior_title and not entry_title:
        assessment.level = "senior"
        assessment.gate = True
        assessment.gate_reason = f"Senior-level title ({senior_title.group(0).strip()})"
        assessment.senior_signals.append(assessment.gate_reason)
        assessment.level_score = 0.0
        return assessment

    if _DOCTORATE_TITLE.search(scrubbed_title):
        assessment.level = "senior"
        assessment.gate = True
        assessment.gate_reason = "Doctorate-level role (PhD in title)"
        assessment.senior_signals.append(assessment.gate_reason)
        assessment.level_score = 0.0
        return assessment

    if numeral_level == "senior":
        assessment.level = "senior"
        assessment.gate = True
        assessment.gate_reason = f"Senior-level title ({numeral_signal})"
        assessment.senior_signals.append(assessment.gate_reason)
        assessment.level_score = 0.0
        return assessment

    if years.required is not None and years.required > MAX_REQUIRED_YEARS:
        assessment.level = "senior"
        assessment.gate = True
        assessment.gate_reason = f"Requires {years.required}+ years of experience"
        assessment.senior_signals.append(assessment.gate_reason)
        assessment.level_score = 0.0
        return assessment

    # ---- entry-level evidence ------------------------------------------------
    years_needed = years.required
    explicit_entry = bool(entry_title) or numeral_level == "entry"
    description_entry = any(pattern.search(clean_text) for pattern in _ENTRY_DESCRIPTION)

    if entry_title:
        assessment.entry_signals.append(f"entry-level title ({entry_title.group(0).strip().lower()})")
    if numeral_level == "entry":
        assessment.entry_signals.append(numeral_signal)
    if years_needed is not None and years_needed <= 1:
        assessment.entry_signals.append("1 year or less required")
    if description_entry:
        assessment.entry_signals.append("description targets early-career candidates")

    scope_hits = sum(1 for pattern in _SCOPE_SIGNALS if pattern.search(clean_text))
    if scope_hits:
        assessment.senior_signals.append(f"{scope_hits} senior-scope phrase(s)")

    # ---- level + score ---------------------------------------------------------
    # "2+ years" is reachable with internships but is not a new-grad role, and a
    # numbered level (II) caps the optimism of a low years mention.
    if explicit_entry:
        assessment.level = "entry"
        assessment.level_score = 1.0 if (years_needed is None or years_needed <= 2) else 0.6
    elif numeral_level == "junior_mid":
        assessment.level = "junior_mid"
        assessment.level_score = 0.6 if (years_needed is None or years_needed <= 2) else 0.35
    elif years_needed is not None and years_needed <= 1:
        assessment.level = "entry"
        assessment.level_score = 0.9
    elif description_entry and (years_needed is None or years_needed <= 2):
        assessment.level = "entry"
        assessment.level_score = 0.85
    elif years_needed == 2:
        assessment.level = "junior_mid"
        assessment.level_score = 0.65
    elif years_needed == 3:
        assessment.level = "mid"
        assessment.level_score = 0.6 if description_entry else 0.3
    else:
        assessment.level = "unknown"
        assessment.level_score = 0.5

    # A role that states no minimum but "prefers" five or more years is
    # senior-leaning even though the preference is not a hard requirement.
    prefers_senior = years_needed is None and (years.preferred or 0) >= 5
    if prefers_senior:
        assessment.senior_signals.append(f"prefers {years.preferred}+ years")

    # Senior-scope language lowers confidence in an unlabelled role.
    if scope_hits and assessment.level in {"unknown", "junior_mid", "mid"}:
        assessment.level_score = max(0.1, assessment.level_score - 0.12 * min(scope_hits, 3))

    if prefers_senior and assessment.level == "unknown":
        assessment.level_score = min(assessment.level_score, 0.3)

    return assessment
