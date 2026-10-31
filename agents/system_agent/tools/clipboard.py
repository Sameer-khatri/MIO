import ctypes
from ctypes import wintypes

try:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = wintypes.BOOL

    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = ctypes.c_void_p
    user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
except AttributeError:
    user32 = None
    kernel32 = None

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040


def get_clipboard_text() -> dict:
    """Reads UTF-16 Unicode text currently stored in the Windows clipboard."""
    if not user32 or not kernel32:
        return {"success": False, "text": "", "message": "Windows API unavailable."}

    if not user32.OpenClipboard(0):
        return {"success": False, "text": "", "message": "Failed to open clipboard."}

    try:
        h_mem = user32.GetClipboardData(CF_UNICODETEXT)
        if not h_mem:
            return {"success": True, "text": "", "message": "Clipboard is empty."}

        ptr = kernel32.GlobalLock(h_mem)
        if not ptr:
            return {"success": False, "text": "", "message": "Failed to lock clipboard memory."}

        try:
            val = ctypes.c_wchar_p(ptr).value or ""
            return {
                "success": True,
                "text": val,
                "length": len(val),
                "message": f"Clipboard text ({len(val)} chars):\n{val[:300]}{'...' if len(val) > 300 else ''}" if val else "Clipboard is empty."
            }
        finally:
            kernel32.GlobalUnlock(h_mem)
    finally:
        user32.CloseClipboard()


def set_clipboard_text(text: str) -> dict:
    """Copies text to the Windows clipboard."""
    if text is None:
        return {"success": False, "message": "Cannot copy None to clipboard."}

    if not user32 or not kernel32:
        return {"success": False, "message": "Windows API unavailable."}

    content_str = str(text)

    if not user32.OpenClipboard(0):
        return {"success": False, "message": "Failed to open clipboard."}

    try:
        user32.EmptyClipboard()
        encoded = (content_str + "\0").encode("utf-16le")
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE | GMEM_ZEROINIT, len(encoded))
        if not h_mem:
            return {"success": False, "message": "GlobalAlloc memory allocation failed."}

        ptr = kernel32.GlobalLock(h_mem)
        if not ptr:
            return {"success": False, "message": "GlobalLock failed."}

        try:
            ctypes.memmove(ptr, encoded, len(encoded))
        finally:
            kernel32.GlobalUnlock(h_mem)

        user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        return {
            "success": True,
            "text": content_str,
            "length": len(content_str),
            "message": f"Copied {len(content_str)} characters to clipboard."
        }
    finally:
        user32.CloseClipboard()


def clear_clipboard() -> dict:
    """Empties all contents from the Windows clipboard."""
    if not user32:
        return {"success": False, "message": "Windows API unavailable."}

    if not user32.OpenClipboard(0):
        return {"success": False, "message": "Failed to open clipboard."}

    try:
        user32.EmptyClipboard()
        return {"success": True, "message": "Clipboard cleared successfully."}
    finally:
        user32.CloseClipboard()
