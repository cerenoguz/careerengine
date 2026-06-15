POSITIVE_AUTH_SIGNALS = [
    "opt",
    "stem opt",
    "f-1",
    "f1",
    "cpt",
    "h-1b",
    "h1b",
    "visa sponsorship",
    "sponsorship available",
    "open to sponsorship",
    "e-verify",
    "international students",
]

NEGATIVE_AUTH_SIGNALS = [
    "no sponsorship",
    "will not sponsor",
    "unable to sponsor",
    "must not require sponsorship",
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


def find_positive_auth_signals(text: str) -> list[str]:
    normalized_text = text.lower()
    return [signal for signal in POSITIVE_AUTH_SIGNALS if signal in normalized_text]


def find_negative_auth_signals(text: str) -> list[str]:
    normalized_text = text.lower()
    return [signal for signal in NEGATIVE_AUTH_SIGNALS if signal in normalized_text]


def classify_eligibility(text: str) -> tuple[str, list[str], list[str]]:
    positive_signals = find_positive_auth_signals(text)
    negative_signals = find_negative_auth_signals(text)

    if negative_signals:
        return "likely_incompatible", positive_signals, negative_signals

    if positive_signals:
        return "likely_compatible", positive_signals, negative_signals

    return "unclear", positive_signals, negative_signals