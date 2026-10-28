"""Smoke test to verify project setup, dependencies, configuration, and environment."""

import sys
from pathlib import Path
import config.settings as settings


def test_python_version():
    """Ensure Python version is 3.10 or higher."""
    assert sys.version_info >= (3, 10), f"Python version must be >= 3.10, found: {sys.version}"


def test_required_dependencies_importable():
    """Verify all critical framework packages can be imported without error."""
    import streamlit
    import plotly
    import pandas
    import numpy
    import sklearn
    import joblib

    assert streamlit.__version__ is not None
    assert plotly.__version__ is not None
    assert pandas.__version__ is not None
    assert numpy.__version__ is not None
    assert sklearn.__version__ is not None
    assert joblib.__version__ is not None


def test_settings_and_paths():
    """Verify configuration settings and runtime directories exist."""
    assert settings.APP_TITLE.startswith("NABHCHAKRA")
    assert settings.RANDOM_SEED == 42
    assert settings.FLEET_SIZE > 0
    assert settings.BASE_DIR.exists()
    assert settings.DATA_DIR.exists()
    assert settings.MODELS_DIR.exists()
    assert "engine_temp_c" in settings.SENSOR_THRESHOLDS
    assert "failure_risk" in settings.PRIORITY_WEIGHTS


def test_gitignore_contains_critical_patterns():
    """Verify .gitignore contains exclusions for .venv, __pycache__, .env, *.pyc."""
    gitignore_path = settings.BASE_DIR / ".gitignore"
    assert gitignore_path.exists(), ".gitignore file must exist"
    
    content = gitignore_path.read_text(encoding="utf-8")
    for pattern in [".venv/", "__pycache__/", "*.py", ".env"]:
        assert pattern in content, f"Expected '{pattern}' in .gitignore"
