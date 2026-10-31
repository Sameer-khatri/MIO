import datetime
import os
import subprocess
import tempfile


def take_screenshot(filename: str | None = None, destination_folder: str | None = None) -> dict:
    """
    Captures a full screenshot of the primary Windows screen and saves it as a PNG file.
    Defaults to saving on the Desktop with a timestamped name.
    """
    try:
        if not destination_folder:
            dest_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(dest_dir):
                dest_dir = os.path.join(os.path.expanduser("~"), "Pictures")
        else:
            dest_dir = os.path.abspath(os.path.expanduser(destination_folder))

        os.makedirs(dest_dir, exist_ok=True)

        if not filename:
            ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            fname = f"MIO_Screenshot_{ts}.png"
        else:
            fname = filename.strip()
            if not fname.lower().endswith(".png"):
                fname += ".png"

        target_path = os.path.join(dest_dir, fname)
        abs_target = os.path.abspath(target_path)

        # Write clean temporary PowerShell script to avoid command-line escaping issues
        ps_code = """param([string]$targetPath)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bitmap.Save($targetPath, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
"""
        with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8") as ps_file:
            ps_file.write(ps_code)
            ps_path = ps_file.name

        try:
            subprocess.check_output(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_path, abs_target],
                stderr=subprocess.STDOUT,
                timeout=10
            )
        except subprocess.CalledProcessError as err:
            err_msg = err.output.decode('utf-8', errors='ignore') if isinstance(err.output, bytes) else str(err.output)
            return {
                "success": False,
                "path": "",
                "message": f"Failed to capture screenshot: {err_msg.strip()}"
            }
        finally:
            if os.path.exists(ps_path):
                os.remove(ps_path)

        if os.path.exists(abs_target):
            size_kb = round(os.path.getsize(abs_target) / 1024, 1)
            return {
                "success": True,
                "path": abs_target,
                "filename": fname,
                "size_kb": size_kb,
                "message": f"Captured screenshot: '{fname}' ({size_kb} KB) saved to {dest_dir}."
            }
        else:
            return {
                "success": False,
                "path": abs_target,
                "message": "Screenshot file was not created."
            }
    except Exception as err:
        return {
            "success": False,
            "path": "",
            "message": f"Failed to capture screenshot: {err}"
        }

