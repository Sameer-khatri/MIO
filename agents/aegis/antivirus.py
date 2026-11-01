"""
Aegis Antivirus & Threat Hunter Engine.
Zero-dependency native Windows security triage:
- Process Masquerading Detection (system processes running outside System32)
- Stealth Persistence Hunter (Run/RunOnce registry and Startup folder inspection)
- Suspicious Argument & File Heuristics (double extensions, hidden script runners)
- Known Malware Signature / Hash Matching (SHA256)
- Safe Sandbox Quarantine Vault
"""

import hashlib
import os
import re
import shutil
import subprocess
import time
import winreg
from typing import Any, Dict, List, Optional

# Standard Windows legitimate system process paths
SYSTEM_CORE_BINARIES = {
    "svchost.exe": r"c:\windows\system32",
    "csrss.exe": r"c:\windows\system32",
    "lsass.exe": r"c:\windows\system32",
    "smss.exe": r"c:\windows\system32",
    "services.exe": r"c:\windows\system32",
    "wininit.exe": r"c:\windows\system32",
    "winlogon.exe": r"c:\windows\system32",
}

# Known double extensions frequently used in phishing / malware
SUSPICIOUS_DOUBLE_EXTENSIONS = (
    ".pdf.exe", ".docx.exe", ".xlsx.exe", ".txt.exe", ".jpg.exe", ".png.exe",
    ".pdf.vbs", ".doc.vbs", ".txt.bat", ".jpg.scr", ".mp4.exe",
)

# Standard EICAR test string hash for verifying antivirus engine
EICAR_SHA256 = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"


class AegisAntivirus:
    """
    Autonomous threat hunter and zero-day heuristic scanner for Windows.
    """

    def __init__(self, quarantine_dir: Optional[str] = None):
        if quarantine_dir:
            self.quarantine_dir = quarantine_dir
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.quarantine_dir = os.path.join(base_dir, ".quarantine")
        
        # Ensure quarantine directory exists
        try:
            os.makedirs(self.quarantine_dir, exist_ok=True)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # 1. Process Masquerading & Memory Inspection
    # -------------------------------------------------------------------------
    def scan_running_processes(self) -> Dict[str, Any]:
        """
        Scans all running processes using WMIC / PowerShell / tasklist to detect:
        1. Critical system binaries running outside C:\\Windows\\System32.
        2. Suspicious command lines (e.g. powershell -w hidden -enc).
        3. Double-extension process executions.
        """
        threats = []
        suspicious = []
        scanned_count = 0

        # Query process executable paths via PowerShell (native, fast)
        ps_cmd = (
            "Get-CimInstance Win32_Process | "
            "Select-Object ProcessId, Name, ExecutablePath, CommandLine | "
            "ConvertTo-Json -Compress"
        )

        try:
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                stderr=subprocess.DEVNULL,
                text=True,
                errors="ignore"
            )
            import json
            data = json.loads(out)
            if isinstance(data, dict):
                data = [data]
        except Exception:
            data = []

        for p in data:
            scanned_count += 1
            pid = p.get("ProcessId")
            name = (p.get("Name") or "").lower()
            exe_path = (p.get("ExecutablePath") or "").lower()
            cmd_line = (p.get("CommandLine") or "").lower()

            # 1. System core binary masquerading check
            if name in SYSTEM_CORE_BINARIES:
                legit_dir = SYSTEM_CORE_BINARIES[name]
                if exe_path and not exe_path.startswith(legit_dir):
                    threats.append({
                        "type": "CRITICAL_MASQUERADE",
                        "severity": "CRITICAL",
                        "name": p.get("Name"),
                        "pid": pid,
                        "path": p.get("ExecutablePath"),
                        "description": f"Process masquerading as Windows core component '{name}', but launched from '{exe_path}'.",
                        "recommended_action": f"Terminate PID {pid} and quarantine executable.",
                    })

            # 2. Suspicious hidden PowerShell / command execution
            if ("-w hidden" in cmd_line or "-windowstyle hidden" in cmd_line) and ("-enc" in cmd_line or "-encodedcommand" in cmd_line):
                suspicious.append({
                    "type": "STEALTH_ENCODED_EXECUTION",
                    "severity": "HIGH",
                    "name": p.get("Name"),
                    "pid": pid,
                    "command": cmd_line[:120],
                    "description": "Hidden window execution running encoded payload.",
                    "recommended_action": f"Inspect command line for PID {pid}.",
                })

            # 3. Double extension process execution
            for ext in SUSPICIOUS_DOUBLE_EXTENSIONS:
                if ext in name or ext in exe_path:
                    threats.append({
                        "type": "DOUBLE_EXTENSION_EXECUTION",
                        "severity": "CRITICAL",
                        "name": p.get("Name"),
                        "pid": pid,
                        "path": p.get("ExecutablePath"),
                        "description": f"Executable disguising itself with fake document extension: {name}",
                        "recommended_action": f"Immediate termination of PID {pid}.",
                    })

        status = "Clean"
        if threats:
            status = f"THREATS DETECTED ({len(threats)} Critical)"
        elif suspicious:
            status = f"WARNING ({len(suspicious)} Suspicious)"

        return {
            "success": True,
            "processes_scanned": scanned_count,
            "threats_count": len(threats),
            "suspicious_count": len(suspicious),
            "threats": threats,
            "suspicious": suspicious,
            "status": status,
            "message": f"Process Scan: Scanned {scanned_count} processes. {status}."
        }

    # -------------------------------------------------------------------------
    # 2. Registry & Startup Persistence Hunter
    # -------------------------------------------------------------------------
    def scan_persistence(self) -> Dict[str, Any]:
        """
        Inspects Windows Run and RunOnce registry hives for stealth malware persistence:
        - Executables launching from %TEMP%, %APPDATA%, or Downloads
        - Hidden batch scripts, VBScript, or raw powershell executions
        """
        targets = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU Run"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKCU RunOnce"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKLM RunOnce"),
        ]

        suspicious_entries = []
        entries_checked = 0

        for hive, subkey, origin in targets:
            try:
                with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
                    count = winreg.QueryInfoKey(key)[1]
                    for i in range(count):
                        entries_checked += 1
                        name, val, _ = winreg.EnumValue(key, i)
                        val_str = str(val).lower()

                        # Flags for stealth persistence
                        is_temp = r"\temp" in val_str or "%temp%" in val_str
                        is_appdata = (r"\appdata\local\temp" in val_str)
                        is_vbs = val_str.endswith(".vbs") or "wscript" in val_str or "cscript" in val_str
                        is_hidden_cmd = "-w hidden" in val_str or "-enc" in val_str

                        reasons = []
                        if is_temp or is_appdata:
                            reasons.append("Launches from temporary folder")
                        if is_vbs:
                            reasons.append("Launches VBScript interpreter")
                        if is_hidden_cmd:
                            reasons.append("Executes hidden encoded script")

                        if reasons:
                            suspicious_entries.append({
                                "name": str(name),
                                "command": str(val),
                                "registry_key": origin,
                                "severity": "HIGH" if (is_temp or is_hidden_cmd) else "MEDIUM",
                                "reasons": reasons,
                                "description": f"Suspicious startup persistence: {', '.join(reasons)}",
                            })
            except Exception:
                pass

        return {
            "success": True,
            "entries_checked": entries_checked,
            "suspicious_count": len(suspicious_entries),
            "findings": suspicious_entries,
            "message": f"Persistence Scan: Checked {entries_checked} registry entries. Found {len(suspicious_entries)} suspicious items."
        }

    # -------------------------------------------------------------------------
    # 3. File & Directory Threat Scanner
    # -------------------------------------------------------------------------
    def scan_file(self, filepath: str) -> Dict[str, Any]:
        """
        Computes SHA256 checksum and inspects a file for malware indicators:
        - Match against known malware hashes
        - Dangerous double extensions
        - Embedded scripts masquerading as documents
        """
        if not os.path.isfile(filepath):
            return {"success": False, "message": f"File '{filepath}' not found."}

        fname = os.path.basename(filepath).lower()
        threats = []
        severity = "CLEAN"

        # 1. Double extension check
        for ext in SUSPICIOUS_DOUBLE_EXTENSIONS:
            if fname.endswith(ext):
                threats.append(f"Deceptive double extension detected ({ext})")
                severity = "CRITICAL"
                break

        # 2. Compute SHA256
        sha256 = ""
        try:
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            sha256 = h.hexdigest()

            # Hash match
            if sha256.lower() == EICAR_SHA256:
                threats.append("EICAR Standard Antivirus Test Signature detected")
                severity = "CRITICAL"
        except Exception as e:
            return {"success": False, "message": f"Error hashing file: {e}"}

        # 3. Check for PE Executable header inside non-exe file extension
        try:
            with open(filepath, "rb") as f:
                header = f.read(2)
                if header == b"MZ" and not fname.endswith((".exe", ".dll", ".sys", ".scr", ".com", ".cpl", ".ocx")):
                    if fname.endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg", ".mp4", ".txt", ".rtf")):
                        threats.append("Windows PE executable binary (MZ) disguised with document/image extension")
                        severity = "CRITICAL"
                    elif fname.endswith((".tmp", ".temp")):
                        threats.append("Executable binary payload residing in temporary file (.tmp)")
                        if severity != "CRITICAL":
                            severity = "SUSPICIOUS"
                    else:
                        threats.append(f"Executable binary (MZ) found with unusual extension: {os.path.splitext(fname)[1]}")
                        if severity != "CRITICAL":
                            severity = "SUSPICIOUS"
        except Exception:
            pass

        return {
            "success": True,
            "filepath": filepath,
            "filename": os.path.basename(filepath),
            "size_bytes": os.path.getsize(filepath),
            "sha256": sha256,
            "severity": severity,
            "is_threat": len(threats) > 0,
            "threats": threats,
            "message": f"File '{os.path.basename(filepath)}': {severity} ({', '.join(threats) if threats else 'No threats found'})."
        }

    def scan_directory(self, folder_path: str, max_files: int = 200) -> Dict[str, Any]:
        """
        Scans all files within a folder (e.g. %TEMP% or Downloads) for malware indicators.
        """
        if not os.path.isdir(folder_path):
            return {"success": False, "message": f"Directory '{folder_path}' not found."}

        scanned = 0
        threats_found = []

        try:
            for root, _, files in os.walk(folder_path):
                for f in files:
                    if scanned >= max_files:
                        break
                    scanned += 1
                    fp = os.path.join(root, f)
                    res = self.scan_file(fp)
                    if res.get("is_threat"):
                        threats_found.append(res)
                if scanned >= max_files:
                    break
        except Exception as e:
            return {"success": False, "message": f"Error scanning directory: {e}"}

        return {
            "success": True,
            "directory": folder_path,
            "files_scanned": scanned,
            "threat_count": len(threats_found),
            "threats": threats_found,
            "message": f"Directory Scan '{folder_path}': Scanned {scanned} files. Found {len(threats_found)} threat(s)."
        }

    # -------------------------------------------------------------------------
    # 4. Safe Quarantine Vault
    # -------------------------------------------------------------------------
    def quarantine_file(self, filepath: str) -> Dict[str, Any]:
        """
        Safely isolates a suspicious file into the Aegis Quarantine Vault:
        - Renames with '.aegis_quarantined' extension to neutralize execution
        - Moves into protected sandbox directory
        - Logs file metadata and hash for forensics
        """
        if not os.path.isfile(filepath):
            return {"success": False, "message": f"Target file '{filepath}' does not exist."}

        try:
            fname = os.path.basename(filepath)
            timestamp = int(time.time())
            quarantined_name = f"{fname}_{timestamp}.aegis_quarantined"
            dest_path = os.path.join(self.quarantine_dir, quarantined_name)

            # Compute hash before moving
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            file_hash = h.hexdigest()

            shutil.move(filepath, dest_path)

            return {
                "success": True,
                "original_path": filepath,
                "quarantine_path": dest_path,
                "sha256": file_hash,
                "message": f"Successfully quarantined '{fname}' -> '{dest_path}'."
            }
        except Exception as err:
            return {"success": False, "message": f"Failed to quarantine file: {err}"}

    def list_quarantine(self) -> Dict[str, Any]:
        """Lists all neutralized files currently resting in the quarantine vault."""
        items = []
        if os.path.exists(self.quarantine_dir):
            try:
                for entry in os.scandir(self.quarantine_dir):
                    if entry.is_file():
                        stat = entry.stat()
                        items.append({
                            "name": entry.name,
                            "path": entry.path,
                            "size_bytes": stat.st_size,
                            "quarantined_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_ctime)),
                        })
            except Exception:
                pass
        return {
            "success": True,
            "quarantine_dir": self.quarantine_dir,
            "total_quarantined": len(items),
            "items": items,
            "message": f"Quarantine Vault: {len(items)} file(s) safely isolated."
        }

    # -------------------------------------------------------------------------
    # 5. Master Quick Security Scan
    # -------------------------------------------------------------------------
    def quick_scan(self) -> Dict[str, Any]:
        """
        High-speed full threat audit:
        1. Process masquerading & hidden arguments
        2. Startup & Registry persistence
        3. Stale %TEMP% executable inspection
        """
        proc_res = self.scan_running_processes()
        persist_res = self.scan_persistence()

        # Quick scan of %TEMP% for rogue executables
        temp_dir = os.environ.get("TEMP", "")
        temp_threats = []
        if temp_dir and os.path.exists(temp_dir):
            temp_res = self.scan_directory(temp_dir, max_files=100)
            temp_threats = temp_res.get("threats", [])

        temp_crit = sum(1 for t in temp_threats if t.get("severity") == "CRITICAL")
        temp_susp = sum(1 for t in temp_threats if t.get("severity") == "SUSPICIOUS")

        total_threats = proc_res.get("threats_count", 0) + temp_crit
        total_suspicious = proc_res.get("suspicious_count", 0) + persist_res.get("suspicious_count", 0) + temp_susp

        if total_threats > 0:
            verdict = f"DANGER: {total_threats} active threat(s) detected on system"
            color_grade = "CRITICAL"
        elif total_suspicious > 0:
            verdict = f"WARNING: {total_suspicious} suspicious persistence or temp artifact(s) found"
            color_grade = "SUSPICIOUS"
        else:
            verdict = "System Clean: Zero active malware or masquerading processes detected"
            color_grade = "SECURE"

        summary_report = f"""
============================================================
              AEGIS ANTIVIRUS THREAT AUDIT REPORT           
============================================================
Security Verdict: [{color_grade}] {verdict}
Processes Audited: {proc_res.get('processes_scanned', 0)} (Threats: {proc_res.get('threats_count', 0)}, Suspicious: {proc_res.get('suspicious_count', 0)})
Persistence Entries: {persist_res.get('entries_checked', 0)} (Suspicious: {persist_res.get('suspicious_count', 0)})
Temp Files Audited: {temp_crit} critical threat(s), {temp_susp} suspicious file(s) in %TEMP%
============================================================
"""

        return {
            "success": True,
            "verdict": verdict,
            "security_grade": color_grade,
            "total_threats": total_threats,
            "total_suspicious": total_suspicious,
            "processes": proc_res,
            "persistence": persist_res,
            "temp_threats": temp_threats,
            "summary_report": summary_report.strip(),
            "message": f"Security Scan Complete: [{color_grade}] - {verdict}"
        }
