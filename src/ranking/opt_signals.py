import re


# Lower-case terms matched on lower-cased text. OPT and CPT are handled
# separately because they must be upper-case to avoid "opt-in" and "opt out".
POSITIVE_AUTH_SIGNALS = [
    "stem opt",
    "f-1",
    "f1",
    "h-1b",
    "h1b",
    "international students",
]

NEGATIVE_AUTH_SIGNALS = [
    "must be authorized to work permanently",
    "u.s. citizen required",
    "us citizen required",
    "u.s. citizenship required",
    "security clearance required",
    "secret clearance",
    "top secret clearance",
    "itar",
    "export control",
    "permanent resident only",
    "green card required",
]

_UPPERCASE_ACRONYM_SIGNALS = {
    "opt": re.compile(r"\bOPT\b(?![-\s]?(?:in|out)\b)"),
    "cpt": re.compile(r"\bCPT\b"),
}


def _contains_signal(normalized_text: str, signal: str) -> bool:
    """
    Match a signal as a whole term, not as letters inside another word.

    "itar" must not match "military". Short acronyms that are also standalone
    words in other contexts can still match; this only guards against
    substring hits.
    """
    pattern = rf"(?<![a-z0-9]){re.escape(signal)}(?![a-z0-9])"
    return re.search(pattern, normalized_text) is not None


# ---------------------------------------------------------------------------
# Sponsorship language
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n|;")
# Periods inside abbreviations must not end a sentence ("certain U.S. visa categories").
_ABBREVIATIONS = re.compile(r"\b(U)\.(S)\.|\b(e)\.(g)\.|\b(i)\.(e)\.", re.IGNORECASE)

_SPONSORSHIP_WORD = re.compile(r"\bsponsor(?:s|ed|ing|ship)?\b", re.IGNORECASE)
_SPONSORSHIP_NOUN = re.compile(r"\bsponsorship\b", re.IGNORECASE)
_IMMIGRATION_CONTEXT = re.compile(
    r"\bvisas?\b|\bh-?1b\b|work (?:authori[sz]ation|permit)|employment (?:authori[sz]ation|eligibility|visa|sponsorship)|"
    r"immigration|green card|authori[sz]ed to work|eligible to work|right to work|"
    r"legally (?:authori[sz]ed|eligible)|\bOPT\b|\bstem opt\b|\bf-?1\b",
    re.IGNORECASE,
)
# Sponsorship that has nothing to do with work authorization.
_NOT_IMMIGRATION = re.compile(
    r"export (?:licen[sc]e|law|control)|clearance|marketing|conference|meetup|\bevents?\b|community|open[\s-]source|"
    r"charit|scholarship|(?:executive|technical|business|product)(?:\s+\w+)?\s+sponsor\b|"
    r"sponsor(?:ed)? (?:a|the) (?:team|project|lunch)",
    re.IGNORECASE,
)
# A short bare statement such as "No sponsorship available." is about visas.
_SHORT_SENTENCE_WORDS = 10

# Phrases that contain a negation word but do not negate.
_FALSE_NEGATION = re.compile(r"\bno matter\b|\bnot only\b|\bnot just\b|\bnot limited\b", re.IGNORECASE)
_NEGATION = re.compile(
    r"\b(?:not|no|never|cannot|unable|without|neither|nor|ineligible)\b|n't\b|\bcan not\b",
    re.IGNORECASE,
)
# "Must be authorized to work now or in the future without sponsorship."
_REQUIRES_NO_SPONSORSHIP = re.compile(
    r"(?:now or in the future|in the future|at any time).{0,40}(?:require|need).{0,30}sponsorship|"
    r"(?:require|need)s?\s+(?:visa\s+|employment\s+)?sponsorship.{0,40}(?:now or in the future|in the future)|"
    r"(?:must|need to|should)\s+(?:already\s+)?(?:hold|have)\s+(?:an?\s+)?(?:existing|current|valid)\s+"
    r"(?:right|authori[sz]ation|permission)\s+to\s+work",
    re.IGNORECASE,
)
# "We do sponsor visas! However, we aren't able to for every role" is a caveat
# on an offer of sponsorship, not a refusal.
_HEDGED = re.compile(
    r"\bevery (?:role|candidate|position|case|applicant|situation)\b|\bnot (?:always|every)\b|"
    r"\bin every case\b|\bfor all (?:roles|candidates|positions)\b",
    re.IGNORECASE,
)
_AVAILABILITY_CUE = re.compile(
    r"\b(?:available|offer(?:s|ed|ing)?|provide[sd]?|providing|support(?:s|ed|ing)?|"
    r"will|can|may|able to|happy to|pleased to|open to|eligible|consider(?:ed)?|"
    r"we sponsor|sponsors?\s+(?:visas?|h-?1b|work))\b",
    re.IGNORECASE,
)


def _sponsorship_sentences(text: str) -> list[str]:
    """Sentences that are about work-authorization sponsorship."""
    sentences: list[str] = []
    text = _ABBREVIATIONS.sub(lambda m: "".join(g for g in m.groups() if g), text)
    for sentence in _SENTENCE_SPLIT.split(text):
        if not _SPONSORSHIP_WORD.search(sentence):
            continue
        if _NOT_IMMIGRATION.search(sentence):
            continue
        is_short_bare_statement = (
            bool(_SPONSORSHIP_NOUN.search(sentence))
            and len(sentence.split()) <= _SHORT_SENTENCE_WORDS
        )
        if _IMMIGRATION_CONTEXT.search(sentence) or is_short_bare_statement:
            sentences.append(sentence)
    return sentences


def _is_negated(sentence: str) -> bool:
    if _REQUIRES_NO_SPONSORSHIP.search(sentence):
        return True
    return bool(_NEGATION.search(_FALSE_NEGATION.sub(" ", sentence)))


def sponsorship_stance(text: str) -> str:
    """
    Read what a posting says about visa sponsorship: "available",
    "unavailable" or "unclear".

    The decision is made sentence by sentence. A sentence about sponsorship
    that contains any negation ("not available", "unable to", "without",
    "no ... sponsorship") means unavailable, so "Visa sponsorship is not
    available" is never mistaken for a positive signal. Any unavailable
    sentence outweighs a positive one elsewhere in the posting.
    """
    stance = "unclear"

    for sentence in _sponsorship_sentences(text):
        if _HEDGED.search(sentence):
            continue
        if _is_negated(sentence):
            return "unavailable"
        if _AVAILABILITY_CUE.search(sentence):
            stance = "available"

    return stance


# ---------------------------------------------------------------------------
# Eligibility classification
# ---------------------------------------------------------------------------

def find_positive_auth_signals(text: str) -> list[str]:
    normalized_text = text.lower()
    signals = [
        signal
        for signal in POSITIVE_AUTH_SIGNALS
        if _contains_signal(normalized_text, signal)
    ]
    signals.extend(
        name for name, pattern in _UPPERCASE_ACRONYM_SIGNALS.items() if pattern.search(text)
    )

    if sponsorship_stance(text) == "available":
        signals.append("visa sponsorship")

    return signals


def find_negative_auth_signals(text: str) -> list[str]:
    normalized_text = text.lower()
    signals = [
        signal
        for signal in NEGATIVE_AUTH_SIGNALS
        if _contains_signal(normalized_text, signal)
    ]

    if sponsorship_stance(text) == "unavailable":
        signals.append("sponsorship not available")

    return signals


def classify_eligibility(text: str) -> tuple[str, list[str], list[str]]:
    positive_signals = find_positive_auth_signals(text)
    negative_signals = find_negative_auth_signals(text)

    if negative_signals:
        return "likely_incompatible", positive_signals, negative_signals

    if positive_signals:
        return "likely_compatible", positive_signals, negative_signals

    return "unclear", positive_signals, negative_signals
