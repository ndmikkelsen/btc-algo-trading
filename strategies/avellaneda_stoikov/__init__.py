"""Avellaneda-Stoikov Market Making Model.

Implementation of the optimal market making framework from:
"High-frequency trading in a limit order book" (Avellaneda & Stoikov, 2008)
"""

from strategies.avellaneda_stoikov.model import AvellanedaStoikov

__all__ = ["AvellanedaStoikov"]
