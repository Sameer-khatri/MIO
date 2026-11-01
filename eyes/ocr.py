"""
MIO Eyes: Native Windows WinRT OCR Engine
------------------------------------------
Zero-dependency, offline visual text recognition using Windows.Media.Ocr.OcrEngine.
Provides bounding boxes and clickable coordinates for on-screen text and buttons.
"""

import json
import os
import subprocess
import tempfile
from typing import Optional

from eyes.guard import SafeEyeShutter, redact_sensitive_text

_OCR_POWERSHELL_SCRIPT = """
param(
    [string]$ImagePath
)

try {
    Add-Type -AssemblyName System.Drawing
    Add-Type -AssemblyName System.Runtime.WindowsRuntime

    [void][Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
    [void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
    [void][Windows.Storage.StorageFile, Windows.Foundation, ContentType = WindowsRuntime]

    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if ($null -eq $engine) {
        Write-Output '{"success": false, "error": "Failed to initialize Windows OcrEngine"}'
        exit
    }

    $fileTask = [Windows.Storage.StorageFile]::GetFileFromPathAsync($ImagePath)
    $asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.IsGenericMethod } | Select-Object -First 1

    $t1 = $asTaskGeneric.MakeGenericMethod([Windows.Storage.StorageFile]).Invoke($null, @($fileTask))
    $t1.Wait()
    $file = $t1.Result

    $streamTask = $file.OpenAsync([Windows.Storage.FileAccessMode]::Read)
    $asTaskStream = $asTaskGeneric.MakeGenericMethod([Windows.Storage.Streams.IRandomAccessStream]).Invoke($null, @($streamTask))
    $asTaskStream.Wait()
    $stream = $asTaskStream.Result

    $decTask = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
    $asTaskDec = $asTaskGeneric.MakeGenericMethod([Windows.Graphics.Imaging.BitmapDecoder]).Invoke($null, @($decTask))
    $asTaskDec.Wait()
    $decoder = $asTaskDec.Result

    $bmpTask = $decoder.GetSoftwareBitmapAsync()
    $asTaskBmp = $asTaskGeneric.MakeGenericMethod([Windows.Graphics.Imaging.SoftwareBitmap]).Invoke($null, @($bmpTask))
    $asTaskBmp.Wait()
    $softwareBmp = $asTaskBmp.Result

    $ocrTask = $engine.RecognizeAsync($softwareBmp)
    $asTaskOcr = $asTaskGeneric.MakeGenericMethod([Windows.Media.Ocr.OcrResult]).Invoke($null, @($ocrTask))
    $asTaskOcr.Wait()
    $ocrResult = $asTaskOcr.Result

    $words = @()
    foreach ($line in $ocrResult.Lines) {
        foreach ($word in $line.Words) {
            $rx = [int]$word.BoundingRect.X
            $ry = [int]$word.BoundingRect.Y
            $rw = [int]$word.BoundingRect.Width
            $rh = [int]$word.BoundingRect.Height
            $cx = [int]($rx + ($rw / 2))
            $cy = [int]($ry + ($rh / 2))

            $words += @{
                text = $word.Text
                x = $rx
                y = $ry
                width = $rw
                height = $rh
                clickable_x = $cx
                clickable_y = $cy
            }
        }
    }

    $outObj = @{
        success = $true
        text = $ocrResult.Text
        words = $words
    }

    $outObj | ConvertTo-Json -Compress -Depth 4
} catch {
    $errObj = @{
        success = $false
        error = $_.Exception.Message
    }
    $errObj | ConvertTo-Json -Compress
}
"""


def recognize_image(image_path: str) -> dict:
    """Runs Windows native OCR on an image file, returning recognized text and word coordinates."""
    if not os.path.exists(image_path):
        return {"success": False, "error": f"Image file not found: {image_path}"}

    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _OCR_POWERSHELL_SCRIPT, "-ImagePath", os.path.abspath(image_path)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode != 0:
            return {"success": False, "error": proc.stderr.strip() or f"OCR exited with code {proc.returncode}"}

        out = proc.stdout.strip()
        # Find JSON payload
        json_start = out.find("{")
        if json_start == -1:
            return {"success": False, "error": "No JSON returned from OCR engine", "raw": out}

        data = json.loads(out[json_start:])
        if data.get("success") and "text" in data:
            data["text"] = redact_sensitive_text(data["text"])
            for w in data.get("words", []):
                w["text"] = redact_sensitive_text(w["text"])

        return data
    except Exception as e:
        return {"success": False, "error": str(e)}


def capture_and_recognize_region(x: int, y: int, width: int, height: int, window_title: str = "", process_name: str = "") -> dict:
    """
    Safely captures a specific screen region into a temporary RAM/temp buffer, runs OCR,
    and immediately deletes the image buffer. Coordinates returned are relative to the entire desktop screen.
    """
    with SafeEyeShutter(target_title=window_title, target_proc=process_name):
        temp_img = os.path.join(tempfile.gettempdir(), f"mio_eye_frame_{os.getpid()}_{int(tempfile._get_candidate_names().__next__(), 36)}.png")
        
        # Take regional capture using System.Drawing
        ps_capture = f"""
        Add-Type -AssemblyName System.Drawing
        $bmp = New-Object System.Drawing.Bitmap {width}, {height}
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $srcPoint = New-Object System.Drawing.Point {x}, {y}
        $g.CopyFromScreen($srcPoint, [System.Drawing.Point]::Empty, (New-Object System.Drawing.Size {width}, {height}))
        $bmp.Save('{temp_img}', [System.Drawing.Imaging.ImageFormat]::Png)
        $g.Dispose()
        $bmp.Dispose()
        """
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_capture], capture_output=True, timeout=10)
            if not os.path.exists(temp_img):
                return {"success": False, "error": "Failed to capture visual frame for OCR"}

            ocr_res = recognize_image(temp_img)
            # Adjust word coordinates by origin (x, y)
            if ocr_res.get("success"):
                for w in ocr_res.get("words", []):
                    w["x"] += x
                    w["y"] += y
                    w["clickable_x"] += x
                    w["clickable_y"] += y
            return ocr_res
        finally:
            if os.path.exists(temp_img):
                try:
                    os.remove(temp_img)
                except OSError:
                    pass
