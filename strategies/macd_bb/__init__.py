"""MACD + Bollinger Bands Strategy."""

# Strategy class is imported directly from strategy.py by Freqtrade
# Keeping this minimal to avoid import issues during unit testing

__all__ = ["MACDBB"]


def __getattr__(name):
    """Lazy import for MACDBB to avoid freqtrade dependency during unit tests."""
    if name == "MACDBB":
        from strategies.macd_bb.strategy import MACDBB
        return MACDBB
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
