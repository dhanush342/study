# Bharat Tech Atlas — ML Integration Module
# Uses lazy imports to avoid crashes when optional deps (transformers, torch) aren't installed.


def get_classifier():
    from .classifier import StartupSectorClassifier
    return StartupSectorClassifier


def get_predictor():
    from .predictor import GrowthPredictor
    return GrowthPredictor


def get_server():
    from .serving import ModelServer
    return ModelServer
