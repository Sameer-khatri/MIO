"""
Dr. Aegis - Autonomous Laptop Doctor & Hardware Guardian
"""
import os
import sys

_AEGIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _AEGIS_DIR not in sys.path:
    sys.path.insert(0, _AEGIS_DIR)

from .aegis import AegisDoctor
from .antivirus import AegisAntivirus
from .sentinel import AegisSentinel

__all__ = ["AegisDoctor", "AegisAntivirus", "AegisSentinel"]
