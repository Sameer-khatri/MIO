"""
MIO EARS: Vocal Hearing & Auditory Perception Subsystem
========================================================
Provides local, zero-dependency speech recognition and microphone perception for MIO.
Operates as a dedicated, standalone organ alongside MIO Eyes, Hands, and Mouth.

Key Operations:
- listen(timeout, phrase_limit): Listens to default microphone for open speech.
- listen_for(phrases, timeout): Targeted keyword/command matching with high accuracy.
- listen_background(callback): Continuous background listening thread.
- stop_listening(): Halts active background listening.
- is_listening(): Checks whether MIO is actively listening.
- list_microphones(): Enumerates all recording audio devices (Microphone Array, Headset, etc.).
- get_default_microphone(): Returns default recording device.
- is_microphone_available(): Checks if a working microphone is detected.
- get_recognizer_info(): Queries installed Windows Speech Recognition engines.
"""

from ears.devices import (
    list_microphones,
    get_default_microphone,
    is_microphone_available,
    get_recognizer_info,
)
from ears.listener import (
    listen,
    listen_for,
    listen_background,
    stop_listening,
    is_listening,
)

__all__ = [
    "listen",
    "listen_for",
    "listen_background",
    "stop_listening",
    "is_listening",
    "list_microphones",
    "get_default_microphone",
    "is_microphone_available",
    "get_recognizer_info",
]
