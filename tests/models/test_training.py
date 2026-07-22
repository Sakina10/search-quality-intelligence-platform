import pytest

optuna = pytest.importorskip("optuna")

from src.models.train_model import load_training_dataset


def test_load_training_dataset_fallback() -> None:
    """Verifies that load_training_dataset handles fallback synthetic dataset generation."""
    with patch("os.path.exists", return_value=False):
        X_train, X_test, y_train, y_test = load_training_dataset()

        assert X_train is not None
        assert X_test is not None
        assert y_train is not None
        assert y_test is not None
        assert len(X_train) > 0
        assert X_train.shape[1] == 10
