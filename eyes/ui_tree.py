"""
MIO Eyes: Windows Native UI Automation Accessibility Tree
----------------------------------------------------------
Zero-dependency UI element discovery using System.Windows.Automation (UIAutomationClient).
Provides structural discovery of buttons, input fields, checkboxes, and menu items.
"""

import json
import subprocess
from typing import Optional, List

from eyes.guard import SafeEyeShutter, redact_sensitive_text

_UI_TREE_SCRIPT = """
param(
    [Int64]$Hwnd = 0,
    [string]$Query = "",
    [string]$ControlType = "",
    [int]$MaxElements = 50
)

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

if ($Hwnd -eq 0) {
    Write-Output '{"success": false, "error": "No HWND provided"}'
    exit
}

try {
    $root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$Hwnd)
    if ($null -eq $root) {
        Write-Output '{"success": false, "error": "Could not access window element from handle"}'
        exit
    }

    $scope = [System.Windows.Automation.TreeScope]::Descendants
    $condition = [System.Windows.Automation.Condition]::TrueCondition

    if ($ControlType) {
        $ctProp = [System.Windows.Automation.AutomationElement]::ControlTypeProperty
        $ctVal = [System.Windows.Automation.ControlType]::$ControlType
        $condition = New-Object System.Windows.Automation.PropertyCondition($ctProp, $ctVal)
    }

    $elements = $root.FindAll($scope, $condition)
    $results = @()
    $count = 0

    foreach ($el in $elements) {
        $name = $el.Current.Name
        $ct = $el.Current.ControlType.ProgrammaticName.Replace("ControlType.", "")
        $rect = $el.Current.BoundingRectangle

        if ($rect.Width -gt 0 -and $rect.Height -gt 0) {
            $match = $true
            if ($Query -and $name) {
                if ($name.IndexOf($Query, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
                    $match = $false
                }
            } elseif ($Query -and -not $name) {
                $match = $false
            }

            if ($match) {
                $cx = [int]($rect.X + ($rect.Width / 2))
                $cy = [int]($rect.Y + ($rect.Height / 2))
                $results += @{
                    name = $name
                    type = $ct
                    x = [int]$rect.X
                    y = [int]$rect.Y
                    width = [int]$rect.Width
                    height = [int]$rect.Height
                    clickable_x = $cx
                    clickable_y = $cy
                }
                $count++
                if ($count -ge $MaxElements) { break }
            }
        }
    }

    $outObj = @{
        success = $true
        hwnd = $Hwnd
        total_found = $results.Count
        elements = $results
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


def inspect_ui_elements(hwnd: int, query: str = "", control_type: str = "", max_elements: int = 50, window_title: str = "", process_name: str = "") -> dict:
    """
    Queries the native Windows accessibility tree for a given window handle.
    Optionally filters by element name query (case-insensitive substring) or ControlType (e.g. Button, Edit, Text).
    """
    if not hwnd:
        return {"success": False, "error": "Invalid window handle (0)"}

    with SafeEyeShutter(target_title=window_title, target_proc=process_name):
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                _UI_TREE_SCRIPT,
                "-Hwnd",
                str(hwnd),
                "-MaxElements",
                str(max_elements),
            ]
            if query:
                cmd.extend(["-Query", query])
            if control_type:
                cmd.extend(["-ControlType", control_type])

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=12,
            )
            if proc.returncode != 0:
                return {"success": False, "error": proc.stderr.strip() or f"UIAutomation exited with {proc.returncode}"}

            out = proc.stdout.strip()
            json_start = out.find("{")
            if json_start == -1:
                return {"success": False, "error": "No JSON returned from UI tree inspector", "raw": out}

            data = json.loads(out[json_start:])
            if data.get("success") and "elements" in data:
                for el in data["elements"]:
                    if el.get("name"):
                        el["name"] = redact_sensitive_text(el["name"])
            return data
        except Exception as e:
            return {"success": False, "error": str(e)}
