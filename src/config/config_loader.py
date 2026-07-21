import os
from typing import Any, Dict
import yaml  # type: ignore
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingSettings(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_to_file: bool = True
    log_path: str = "logs/platform.log"


class DatabaseSettings(BaseModel):
    host: str = "db"
    port: int = 5432
    name: str = "search_quality"
    user: str = "postgres_admin"
    password: str = Field(..., min_length=8)  # Require secure passwords
    pool_size: int = 20
    max_overflow: int = 10


class APISettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    timeout_seconds: int = 60


class DataGenSettings(BaseModel):
    total_rows: int = 1000000
    batch_size: int = 200000
    random_seed: int = 42
    start_date: str = "2026-06-01"
    end_date: str = "2026-07-20"
    anomaly_simulation: bool = True
    anomaly_date: str = "2026-07-15"
    anomaly_country: str = "United States"
    anomaly_device: str = "Mobile"
    anomaly_latency_multiplier: float = 4.5


class ModelSettings(BaseModel):
    registry_path: str = "models/model_registry.json"
    sqs_predictor_version: str = "1.0.0"
    anomaly_detector_version: str = "1.0.0"
    test_split_ratio: float = 0.2
    time_series_split_folds: int = 5


class Settings(BaseSettings):
    env: str = "prod"
    debug: bool = False
    logging: LoggingSettings = LoggingSettings()
    database: DatabaseSettings
    api: APISettings = APISettings()
    data_generation: DataGenSettings = DataGenSettings()
    model: ModelSettings = ModelSettings()

    # Configure Pydantic to read environment variables prefixed with "PLATFORM_"
    model_config = SettingsConfigDict(
        env_prefix="PLATFORM_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )


def load_yaml_config(file_path: str) -> Dict[str, Any]:
    """Helper function to load and parse a YAML configuration file."""
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r") as f:
        config = yaml.safe_load(f)
        return config if isinstance(config, dict) else {}


def merge_dicts(dict_base: Dict[str, Any], dict_override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merges dictionary override values into the base dictionary."""
    merged = dict_base.copy()
    for key, value in dict_override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def merge_env_vars(config: Dict[str, Any], prefix: str = "PLATFORM_") -> Dict[str, Any]:
    """Manually parses and merges environment variables prefixed with PLATFORM_ into the dictionary

    to prevent constructor arguments from bypassing Pydantic Settings env loaders.
    """
    merged = config.copy()
    for env_key, env_val in os.environ.items():
        if env_key.startswith(prefix):
            key_path = env_key[len(prefix):].lower().split("__")
            curr = merged
            for part in key_path[:-1]:
                if part not in curr:
                    curr[part] = {}
                curr = curr[part]
            # Convert values to correct types if they are simple numbers or booleans
            val: Any = env_val
            if env_val.lower() == "true":
                val = True
            elif env_val.lower() == "false":
                val = False
            elif env_val.isdigit():
                val = int(env_val)
            else:
                try:
                    val = float(env_val)
                except ValueError:
                    pass
            curr[key_path[-1]] = val
    return merged


def get_settings() -> Settings:
    """Centralized configuration loader factory (Singleton pattern).

    Loads base configs, applies environment overrides (e.g. dev_config.yaml),
    and validates everything against the Pydantic schema including environment variables.
    """
    # 1. Determine execution environment (default to 'prod')
    env = os.getenv("PLATFORM_ENV", "prod").lower()

    # 2. Set config file paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    configs_dir = os.path.join(base_dir, "configs")
    
    base_yaml_path = os.path.join(configs_dir, "base_config.yaml")
    override_yaml_path = os.path.join(configs_dir, f"{env}_config.yaml")

    # 3. Load configurations from files
    config_dict = load_yaml_config(base_yaml_path)
    if os.path.exists(override_yaml_path):
        override_dict = load_yaml_config(override_yaml_path)
        config_dict = merge_dicts(config_dict, override_dict)

    # 4. Merge environment variable overrides manually before construction
    config_dict = merge_env_vars(config_dict)

    # 5. Instantiate settings model
    return Settings(**config_dict)


# Export a global instance
settings: Settings = get_settings()
