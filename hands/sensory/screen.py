import datetime
import os
import struct
import subprocess


def _get_default_save_path(custom_name: str = None) -> str:
    user_home = os.path.expanduser("~")
    pictures_dir = os.path.join(user_home, "Pictures")
    screenshots_dir = os.path.join(pictures_dir, "Screenshots")

    if os.path.exists(screenshots_dir):
        save_dir = screenshots_dir
    elif os.path.exists(pictures_dir):
        save_dir = pictures_dir
    else:
        save_dir = os.path.join(user_home, "Desktop")

    if custom_name and custom_name.strip():
        base_name = custom_name.strip()
        if not base_name.lower().endswith(".png"):
            base_name += ".png"
        return os.path.abspath(os.path.join(save_dir, base_name))

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.abspath(os.path.join(save_dir, f"MIO_Screenshot_{timestamp}.png"))


def take_screenshot(custom_name: str = None) -> dict:
    """
    Captures a full-desktop screenshot and saves it directly to PNG format.
    """
    target_path = _get_default_save_path(custom_name)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    ps_script = (
        "param([string]$targetPath) "
        "[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');"
        "[void][System.Reflection.Assembly]::LoadWithPartialName('System.Drawing');"
        "$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
        "$bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height;"
        "$graphics = [System.Drawing.Graphics]::FromImage($bitmap);"
        "$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size);"
        "$bitmap.Save($targetPath, [System.Drawing.Imaging.ImageFormat]::Png);"
        "$graphics.Dispose();"
        "$bitmap.Dispose();"
    )

    try:
        subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_script, "-targetPath", target_path],
            stderr=subprocess.STDOUT
        )

        if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
            size_kb = round(os.path.getsize(target_path) / 1024, 1)
            dim = get_image_dimensions(target_path)
            res_str = f" ({dim['width']}x{dim['height']})" if dim.get("success") else ""
            return {
                "success": True,
                "path": target_path,
                "size_kb": size_kb,
                "resolution": f"{dim.get('width', 0)}x{dim.get('height', 0)}",
                "message": f"Screenshot saved to '{target_path}'{res_str} ({size_kb} KB)."
            }
        else:
            return {"success": False, "path": target_path, "message": "Screenshot file was not created."}
    except Exception as err:
        return {"success": False, "path": target_path, "message": f"Screenshot capture failed: {err}"}


def take_region_screenshot(x: int, y: int, width: int, height: int, custom_name: str = None) -> dict:
    """
    Captures a specific rectangular screen region and saves to PNG.
    """
    target_path = _get_default_save_path(custom_name)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    ps_script = (
        "param([string]$targetPath, [int]$rx, [int]$ry, [int]$rw, [int]$rh) "
        "[void][System.Reflection.Assembly]::LoadWithPartialName('System.Drawing');"
        "$bitmap = New-Object System.Drawing.Bitmap $rw, $rh;"
        "$graphics = [System.Drawing.Graphics]::FromImage($bitmap);"
        "$point = New-Object System.Drawing.Point $rx, $ry;"
        "$size = New-Object System.Drawing.Size $rw, $rh;"
        "$graphics.CopyFromScreen($point, [System.Drawing.Point]::Empty, $size);"
        "$bitmap.Save($targetPath, [System.Drawing.Imaging.ImageFormat]::Png);"
        "$graphics.Dispose();"
        "$bitmap.Dispose();"
    )

    try:
        subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_script,
             "-targetPath", target_path,
             "-rx", str(int(x)), "-ry", str(int(y)),
             "-rw", str(int(width)), "-rh", str(int(height))],
            stderr=subprocess.STDOUT
        )

        if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
            size_kb = round(os.path.getsize(target_path) / 1024, 1)
            return {
                "success": True,
                "path": target_path,
                "size_kb": size_kb,
                "region": {"x": x, "y": y, "width": width, "height": height},
                "message": f"Region screenshot ({width}x{height}) saved to '{target_path}' ({size_kb} KB)."
            }
        return {"success": False, "message": "Region screenshot file was not created."}
    except Exception as err:
        return {"success": False, "message": f"Region capture failed: {err}"}


def get_image_dimensions(png_path: str) -> dict:
    """
    Parses PNG width and height directly from the IHDR binary chunk without external libraries.
    """
    if not os.path.exists(png_path) or not os.path.isfile(png_path):
        return {"success": False, "message": "File not found."}

    try:
        with open(png_path, "rb") as f:
            header = f.read(24)
            # PNG signature is 8 bytes, followed by 4 bytes IHDR length, 4 bytes IHDR type, 4 bytes width, 4 bytes height
            if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
                width, height = struct.unpack(">II", header[16:24])
                return {"success": True, "width": width, "height": height}
        return {"success": False, "message": "Not a standard PNG file."}
    except Exception as err:
        return {"success": False, "message": f"Could not parse image header: {err}"}
