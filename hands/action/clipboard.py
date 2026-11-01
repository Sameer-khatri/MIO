import ctypes
from ctypes import wintypes

try:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.EnumClipboardFormats.argtypes = [wintypes.UINT]
    user32.EnumClipboardFormats.restype = wintypes.UINT
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
except AttributeError:
    user32 = None
    kernel32 = None

CF_TEXT = 1
CF_BITMAP = 2
CF_HDROP = 15
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

CLIPBOARD_FORMAT_NAMES = {
    1: "CF_TEXT",
    2: "CF_BITMAP",
    13: "CF_UNICODETEXT",
    15: "CF_HDROP (Files)",
    16: "CF_LOCALE",
}


def get_clipboard_text() -> dict:
    """Reads current UTF-16 text from the Windows system clipboard."""
    if not user32 or not kernel32:
        return {"success": False, "text": "", "message": "user32/kernel32 is unavailable."}

    if not user32.OpenClipboard(None):
        return {"success": False, "text": "", "message": "Could not open system clipboard."}

    try:
        h_clip = user32.GetClipboardData(CF_UNICODETEXT)
        if not h_clip:
            return {"success": True, "text": "", "message": "Clipboard is empty or does not contain text."}

        p_data = kernel32.GlobalLock(h_clip)
        if not p_data:
            return {"success": False, "text": "", "message": "Could not lock clipboard memory."}

        try:
            text = ctypes.wstring_at(p_data)
            preview = text[:80] + "..." if len(text) > 80 else text
            return {
                "success": True,
                "text": text,
                "length": len(text),
                "message": f"Clipboard content ({len(text)} chars): \"{preview}\""
            }
        finally:
            kernel32.GlobalUnlock(h_clip)
    finally:
        user32.CloseClipboard()


def set_clipboard_text(text: str) -> dict:
    """Writes UTF-16 text to the Windows system clipboard."""
    if not user32 or not kernel32:
        return {"success": False, "message": "user32/kernel32 is unavailable."}

    clean_text = text if isinstance(text, str) else str(text)
    encoded = (clean_text + "\0").encode("utf-16-le")
    byte_len = len(encoded)

    h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, byte_len)
    if not h_mem:
        return {"success": False, "message": "Could not allocate global memory."}

    p_mem = kernel32.GlobalLock(h_mem)
    if not p_mem:
        return {"success": False, "message": "Could not lock global memory."}

    ctypes.memmove(p_mem, encoded, byte_len)
    kernel32.GlobalUnlock(h_mem)

    if not user32.OpenClipboard(None):
        return {"success": False, "message": "Could not open system clipboard."}

    try:
        user32.EmptyClipboard()
        user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        preview = clean_text[:80] + "..." if len(clean_text) > 80 else clean_text
        return {
            "success": True,
            "text": clean_text,
            "length": len(clean_text),
            "message": f"Copied {len(clean_text)} character(s) to clipboard: \"{preview}\""
        }
    finally:
        user32.CloseClipboard()


def append_clipboard_text(text: str, separator: str = "\n") -> dict:
    """Appends text to current clipboard content without replacing it."""
    curr = get_clipboard_text()
    existing = curr.get("text", "")
    new_combined = f"{existing}{separator}{text}" if existing else text
    return set_clipboard_text(new_combined)


def clear_clipboard() -> dict:
    """Empties all contents currently stored in the system clipboard."""
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    if not user32.OpenClipboard(None):
        return {"success": False, "message": "Could not open system clipboard."}

    try:
        user32.EmptyClipboard()
        return {"success": True, "message": "Clipboard cleared successfully."}
    finally:
        user32.CloseClipboard()


def get_clipboard_formats() -> dict:
    """Lists all data formats currently stored in the system clipboard."""
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    if not user32.OpenClipboard(None):
        return {"success": False, "message": "Could not open system clipboard."}

    formats = []
    try:
        fmt = user32.EnumClipboardFormats(0)
        while fmt != 0:
            name = CLIPBOARD_FORMAT_NAMES.get(fmt, f"Format_{fmt}")
            formats.append({"id": fmt, "name": name})
            fmt = user32.EnumClipboardFormats(fmt)

        return {
            "success": True,
            "count": len(formats),
            "format_count": len(formats),
            "formats": formats,
            "message": f"Active clipboard formats: {', '.join(f['name'] for f in formats) if formats else 'Empty'}"
        }
    finally:
        user32.CloseClipboard()
