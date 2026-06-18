import os
from functools import lru_cache

import numpy as np


DEFAULT_SEMANTIC_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SEMANTIC_SHADOW_ENVIRONMENT_VARIABLE = "CAREERENGINE_ENABLE_SEMANTIC_SHADOW"


def semantic_shadow_enabled() -> bool:
    return (
        os.getenv(SEMANTIC_SHADOW_ENVIRONMENT_VARIABLE, "false").lower()
        == "true"
    )


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


def compute_semantic_similarities(
    candidate_profile: str,
    job_descriptions: list[str],
) -> tuple[list[float], str]:
    """
    Compute Sentence-BERT cosine similarity in shadow mode.

    This function never changes CareerEngine ranking. It returns semantic scores
    only for comparison and diagnostics.

    Status values:
    - disabled: semantic shadow mode is off
    - available: semantic scores were calculated
    - unavailable: dependency/model loading failed; lexical scoring continues
    - no_jobs: no descriptions were provided
    """
    if not job_descriptions:
        return [], "no_jobs"

    if not semantic_shadow_enabled():
        return [0.0] * len(job_descriptions), "disabled"

    try:
        model = _load_model()

        embeddings = model.encode(
            [candidate_profile, *job_descriptions],
            batch_size=_get_batch_size(),
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        candidate_embedding = embeddings[0]
        job_embeddings = embeddings[1:]

        scores = np.dot(job_embeddings, candidate_embedding)
        normalized_scores = [
            float(np.clip(score, -1.0, 1.0))
            for score in scores
        ]

        return normalized_scores, "available"

    except Exception as error:
        print(
            "Semantic shadow unavailable. "
            f"Continuing with lexical similarity only: "
            f"{type(error).__name__}: {error}"
        )

        return [0.0] * len(job_descriptions), "unavailable"
