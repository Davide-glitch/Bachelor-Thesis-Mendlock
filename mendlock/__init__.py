"""Mendlock: Verified self-healing locators for end-to-end web tests."""
from .candidates import Candidate, Fingerprint
from .healer import HealConfig, Healer, HealResult
from .model import Model, load_default_model
from .page import HealingFailed, HealingPage, HealingUnavailable

__version__ = "1.0.0"

__all__ = [
    "Candidate",
    "Fingerprint",
    "HealConfig",
    "Healer",
    "HealResult",
    "Model",
    "load_default_model",
    "HealingFailed",
    "HealingPage",
    "HealingUnavailable",
]