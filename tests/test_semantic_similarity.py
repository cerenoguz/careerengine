import numpy as np

from src.ranking import semantic_similarity


def test_semantic_shadow_returns_zero_scores_when_disabled(monkeypatch):
    monkeypatch.setenv("CAREERENGINE_ENABLE_SEMANTIC_SHADOW", "false")

    def fail_if_called():
        raise AssertionError("Model should not load when shadow mode is disabled.")

    monkeypatch.setattr(semantic_similarity, "_load_model", fail_if_called)

    scores, status = semantic_similarity.compute_semantic_similarities(
        "Python backend engineer.",
        ["Build reliable backend APIs.", "Design mobile applications."],
    )

    assert status == "disabled"
    assert scores == [0.0, 0.0]


def test_semantic_shadow_uses_normalized_embeddings(monkeypatch):
    monkeypatch.setenv("CAREERENGINE_ENABLE_SEMANTIC_SHADOW", "true")

    class FakeModel:
        def encode(self, texts, **kwargs):
            assert len(texts) == 3
            return np.array(
                [
                    [1.0, 0.0],
                    [0.8, 0.2],
                    [0.0, 1.0],
                ]
            )

    monkeypatch.setattr(
        semantic_similarity,
        "_load_model",
        lambda: FakeModel(),
    )

    scores, status = semantic_similarity.compute_semantic_similarities(
        "Python backend engineer.",
        ["Backend API role.", "Marketing role."],
    )

    assert status == "available"
    assert scores[0] == 0.8
    assert scores[1] == 0.0
