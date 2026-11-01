"""
MIO Ears: Native WinMM Audio Capture
====================================
Records clean 16-bit 16kHz mono PCM audio directly from the Windows default
recording endpoint using native Windows Multimedia (winmm.dll).
Zero external pip audio dependencies.
"""

import ctypes
from ctypes import wintypes
import math
import os
import struct
import tempfile
import time
import wave
from typing import Optional, Tuple

winmm = ctypes.windll.winmm
WAVE_FORMAT_PCM = 1
WAVE_MAPPER = -1


class WAVEFORMATEX(ctypes.Structure):
    _fields_ = [
        ("wFormatTag", wintypes.WORD),
        ("nChannels", wintypes.WORD),
        ("nSamplesPerSec", wintypes.DWORD),
        ("nAvgBytesPerSec", wintypes.DWORD),
        ("nBlockAlign", wintypes.WORD),
        ("wBitsPerSample", wintypes.WORD),
        ("cbSize", wintypes.WORD),
    ]


class WAVEHDR(ctypes.Structure):
    pass


WAVEHDR._fields_ = [
    ("lpData", ctypes.POINTER(ctypes.c_char)),
    ("dwBufferLength", wintypes.DWORD),
    ("dwBytesRecorded", wintypes.DWORD),
    ("dwUser", ctypes.c_void_p),
    ("dwFlags", wintypes.DWORD),
    ("dwLoops", wintypes.DWORD),
    ("lpNext", ctypes.POINTER(WAVEHDR)),
    ("reserved", ctypes.c_void_p),
]


def calculate_rms(raw_pcm_bytes: bytes) -> float:
    """
    Computes Root Mean Square (RMS) volume amplitude from 16-bit PCM bytes.
    """
    count = len(raw_pcm_bytes) // 2
    if count == 0:
        return 0.0
    format_str = f"<{count}h"
    shorts = struct.unpack(format_str, raw_pcm_bytes[: count * 2])
    sum_squares = sum(s * s for s in shorts)
    return math.sqrt(sum_squares / count)


def record_pcm_to_file(
    duration_seconds: float = 4.0,
    sample_rate: int = 16000,
    channels: int = 1,
    bits_per_sample: int = 16,
) -> Tuple[str, float]:
    """
    Records audio from the default microphone into a temporary WAV file.
    
    Args:
        duration_seconds: Duration to record in seconds (clamped 0.5 to 30.0).
        sample_rate: Sampling frequency in Hz (default 16000 for Whisper).
        channels: Channel count (1 for mono).
        bits_per_sample: Bit depth (16-bit PCM).
        
    Returns:
        Tuple of (wav_file_path, actual_duration)
    """
    duration_seconds = max(0.5, min(float(duration_seconds), 30.0))
    block_align = channels * (bits_per_sample // 8)
    avg_bytes = sample_rate * block_align

    wfx = WAVEFORMATEX()
    wfx.wFormatTag = WAVE_FORMAT_PCM
    wfx.nChannels = channels
    wfx.nSamplesPerSec = sample_rate
    wfx.nAvgBytesPerSec = avg_bytes
    wfx.nBlockAlign = block_align
    wfx.wBitsPerSample = bits_per_sample
    wfx.cbSize = 0

    h_wavein = wintypes.HANDLE()
    res = winmm.waveInOpen(ctypes.byref(h_wavein), WAVE_MAPPER, ctypes.byref(wfx), 0, 0, 0)
    if res != 0:
        raise RuntimeError(f"waveInOpen failed to open recording device (code {res})")

    buffer_size = int(avg_bytes * duration_seconds)
    raw_buffer = (ctypes.c_char * buffer_size)()

    hdr = WAVEHDR()
    hdr.lpData = ctypes.cast(raw_buffer, ctypes.POINTER(ctypes.c_char))
    hdr.dwBufferLength = buffer_size
    hdr.dwBytesRecorded = 0
    hdr.dwFlags = 0
    hdr.dwLoops = 0

    winmm.waveInPrepareHeader(h_wavein, ctypes.byref(hdr), ctypes.sizeof(hdr))
    winmm.waveInAddBuffer(h_wavein, ctypes.byref(hdr), ctypes.sizeof(hdr))
    winmm.waveInStart(h_wavein)

    start_time = time.time()
    time.sleep(duration_seconds)
    actual_duration = time.time() - start_time

    winmm.waveInReset(h_wavein)
    winmm.waveInUnprepareHeader(h_wavein, ctypes.byref(hdr), ctypes.sizeof(hdr))
    winmm.waveInClose(h_wavein)

    bytes_recorded = min(hdr.dwBytesRecorded, buffer_size)
    raw_data = bytes(raw_buffer[:bytes_recorded])

    # Audio Volume Normalization (Peak Gain Boost for quiet microphones)
    num_samples = len(raw_data) // 2
    if num_samples > 0:
        samples = list(struct.unpack(f"<{num_samples}h", raw_data[: num_samples * 2]))
        max_peak = max(abs(s) for s in samples) if samples else 0
        if 50 < max_peak < 24000:
            scale_factor = 24000.0 / max_peak
            normalized_samples = [max(-32767, min(32767, int(s * scale_factor))) for s in samples]
            raw_data = struct.pack(f"<{num_samples}h", *normalized_samples)

    temp_fd, wav_path = tempfile.mkstemp(prefix="mio_ear_", suffix=".wav")
    os.close(temp_fd)

    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(bits_per_sample // 8)
        wf.setframerate(sample_rate)
        wf.writeframes(raw_data)

    return wav_path, round(actual_duration, 2)
