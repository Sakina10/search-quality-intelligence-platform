from src.config.config_loader import get_settings


def test_config_loader_default(monkeypatch) -> None:
    """Verifies that configurations load default parameters correctly."""
    # Ensure environment matches base default
    monkeypatch.setenv("PLATFORM_ENV", "prod")
    monkeypatch.setenv("PLATFORM_DATABASE__PASSWORD", "secure_prod_password")

    config = get_settings()
    assert config.env == "prod"
    assert config.debug is False
    assert config.database.password == "secure_prod_password"
    assert config.database.port == 5432


def test_config_environment_overrides(monkeypatch) -> None:
    """Verifies that development overrides are applied correctly when env is set to dev."""
    monkeypatch.setenv("PLATFORM_ENV", "dev")
    monkeypatch.setenv("PLATFORM_DATABASE__PASSWORD", "secure_dev_password")

    config = get_settings()
    assert config.env == "dev"
    assert config.debug is True
    assert config.database.host == "localhost"  # Dev override
    assert config.database.password == "secure_dev_password"
    assert config.data_generation.total_rows == 10000  # Dev override
