import os
import re
from functools import lru_cache

import numpy as np


DEFAULT_SEMANTIC_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SEMANTIC_ENVIRONMENT_VARIABLE = "CAREERENGINE_ENABLE_SEMANTIC_SHADOW"

# all-MiniLM-L6-v2 silently truncates input to 256 word-pieces, so long
# documents are embedded as several short chunks instead of one truncated one.
CHUNK_WORDS = 110
MAX_JOB_CHUNKS = 4


def semantic_shadow_enabled() -> bool:
    return os.getenv(SEMANTIC_ENVIRONMENT_VARIABLE, "false").lower() == "true"


def _get_batch_size() -> int:
    try:
        return max(1, int(os.getenv("CAREERENGINE_SEMANTIC_BATCH_SIZE", "32")))
    except ValueError:
        return 32


@lru_cache(maxsize=1)
def _load_model():
    """
    Load the semantic model lazily.

    Importing sentence_transformers here keeps normal test runs lightweight and
    lets CareerEngine fall back safely if the dependency or model is unavailable.
    """
    from sentence_transformers import SentenceTransformer

    model_name = os.getenv(
        "CAREERENGINE_SEMANTIC_MODEL",
        DEFAULT_SEMANTIC_MODEL,
    )

    return SentenceTransformer(model_name)


def chunk_text(text: str, *, max_words: int = CHUNK_WORDS, max_chunks: int | None = None) -> list[str]:
    """Split text into chunks that fit the embedding model's window."""
    words = text.split()
    chunks = [
        " ".join(words[start : start + max_words])
        for start in range(0, len(words), max_words)
    ]
    if max_chunks is not None:
        chunks = chunks[:max_chunks]
    return chunks or [""]


def _profile_chunks(profile: str) -> list[str]:
    chunks: list[str] = []
    for paragraph in re.split(r"\n\s*\n", profile):
        paragraph = paragraph.strip()
        if paragraph:
            chunks.extend(chunk_text(paragraph))
    return chunks or [""]


def compute_semantic_similarities(
    candidate_profile: str,
    job_texts: list[str],
) -> tuple[list[float], str]:
    """
    Sentence-BERT similarity between the candidate profile and each job's
    role text, in [-1, 1].

    Both sides are chunked so nothing is lost to the model's 256-token window:
    a job's score is the mean, over its chunks, of the best-matching profile
    chunk. Callers should pass focused role text (responsibilities and
    requirements), not company boilerplate.

    Status values:
    - disabled: semantic scoring is off
    - available: semantic scores were calculated
    - unavailable: dependency/model loading failed; callers fall back to
      neutral semantic credit
    - no_jobs: no texts were provided
    """
    if not job_texts:
        return [], "no_jobs"

    if not semantic_shadow_enabled():
        return [0.0] * len(job_texts), "disabled"

    try:
        model = _load_model()

        profile_chunks = _profile_chunks(candidate_profile)
        job_chunks = [chunk_text(text, max_chunks=MAX_JOB_CHUNKS) for text in job_texts]

        flat_job_chunks = [chunk for chunks in job_chunks for chunk in chunks]

        embeddings = model.encode(
            [*profile_chunks, *flat_job_chunks],
            batch_size=_get_batch_size(),
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        profile_embeddings = embeddings[: len(profile_chunks)]
        job_embeddings = embeddings[len(profile_chunks) :]

        # similarity of every job chunk to its best profile chunk
        best_per_chunk = np.max(job_embeddings @ profile_embeddings.T, axis=1)

        scores: list[float] = []
        cursor = 0
        for chunks in job_chunks:
            window = best_per_chunk[cursor : cursor + len(chunks)]
            cursor += len(chunks)
            scores.append(float(np.clip(np.mean(window), -1.0, 1.0)))

        return scores, "available"

    except Exception as error:
        print(
            "Semantic scoring unavailable. "
            f"Continuing without it: {type(error).__name__}: {error}"
        )

        return [0.0] * len(job_texts), "unavailable"
