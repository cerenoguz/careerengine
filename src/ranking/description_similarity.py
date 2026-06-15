import math
import re
from collections import Counter


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "in", "is", "it", "of", "on", "or", "our", "that",
    "the", "their", "this", "to", "with", "you", "your", "we", "will",
}


def tokenize(text: str) -> list[str]:
    """
    Convert text into normalized tokens.

    This intentionally works on job descriptions, not titles.
    """
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]*", text.lower())
    return [token for token in tokens if token not in STOPWORDS and len(token) > 1]


def cosine_similarity(text_a: str, text_b: str) -> float:
    """
    Compute cosine similarity between two text documents.

    Returns a score from 0.0 to 1.0.
    """
    tokens_a = tokenize(text_a)
    tokens_b = tokenize(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    vector_a = Counter(tokens_a)
    vector_b = Counter(tokens_b)

    shared_terms = set(vector_a) & set(vector_b)

    dot_product = sum(vector_a[term] * vector_b[term] for term in shared_terms)

    magnitude_a = math.sqrt(sum(count * count for count in vector_a.values()))
    magnitude_b = math.sqrt(sum(count * count for count in vector_b.values()))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


def compute_description_similarity(candidate_profile: str, job_description: str) -> float:
    """
    Compare the candidate profile against the job description only.

    The job title should not be passed into this function.
    """
    return cosine_similarity(candidate_profile, job_description)
