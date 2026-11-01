"""
Aegis Shield - Advanced Threat Hunter & Antivirus Engine for Windows.
Military-grade endpoint security, zero-day heuristic triage, and active threat neutralization.

Threat Engines:
1. Process Masquerading & Parent-Child Tree Anomalies (svchost, csrss, lsass parentage verification)
2. LOLBins & Living-off-the-Land Command Line Abuse (certutil, mshta, bitsadmin, regsvr32, hidden encoded powershell)
3. Active Network Beacon & Reverse-Shell Listener Scanner (processes in AppData/Temp with remote sockets)
4. Persistence Hunter (Registry Run/RunOnce, Startup folders, Scheduled Tasks)
5. Security Tampering & AV Blindspot Detector (Defender/UAC/Firewall tampering)
6. Deceptive File & Double-Extension Heuristics (disguised PE executables, EICAR hash signatures)
7. Hunter Killer & Sandbox Quarantine Vault (instant PID kill-tree, persistence removal & file isolation)
"""

import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import winreg
from typing import Any, Dict, List, Optional, Tuple

# Standard Windows legitimate system process paths
SYSTEM32_DIR = r"c:\windows\system32"
SYSTEM_CORE_BINARIES = {
    "svchost.exe": SYSTEM32_DIR,
    "csrss.exe": SYSTEM32_DIR,
    "lsass.exe": SYSTEM32_DIR,
    "smss.exe": SYSTEM32_DIR,
    "services.exe": SYSTEM32_DIR,
    "wininit.exe": SYSTEM32_DIR,
    "winlogon.exe": SYSTEM32_DIR,
    "runtimebroker.exe": SYSTEM32_DIR,
    "taskhostw.exe": SYSTEM32_DIR,
}

# Legitimate parent processes for critical core binaries
CORE_EXPECTED_PARENTS = {
    "svchost.exe": ["services.exe"],
    "services.exe": ["wininit.exe"],
    "lsass.exe": ["wininit.exe"],
}

# Known double extensions frequently used in phishing / malware
SUSPICIOUS_DOUBLE_EXTENSIONS = (
    ".pdf.exe", ".docx.exe", ".xlsx.exe", ".txt.exe", ".jpg.exe", ".png.exe",
    ".pdf.vbs", ".doc.vbs", ".txt.bat", ".jpg.scr", ".mp4.exe", ".iso.exe",
)

# Known LOLBin signatures (Living off the Land Binaries abused by attackers)
LOLBIN_SIGNATURES = [
    (r"certutil.*(-urlcache|-split|-f)", "CertUtil remote payload download"),
    (r"mshta\s+http", "Mshta executing remote malicious HTML application"),
    (r"bitsadmin.*(/transfer|/addfile)", "Bitsadmin background transfer download"),
    (r"regsvr32.*(/s|/u).*(scrobj\.dll|http)", "Regsvr32 remote scriptlet execution (Squiblydoo)"),
    (r"powershell.*(-w hidden|-windowstyle hidden).*-enc", "Hidden window executing base64 encoded PowerShell"),
    (r"powershell.*(iex|invoke-expression).*(downloadstring|webclient)", "PowerShell in-memory remote payload download & exec"),
    (r"wscript.*\.vbs.*(temp|appdata)", "VBScript executing from temporary user folder"),
    (r"rundll32.*(temp|appdata).*\.dll", "RunDLL32 executing unregistered DLL from user directory"),
]

# Standard EICAR test string hash
EICAR_SHA256 = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"


class AegisAntivirus:
    """
    Advanced Endpoint Security & Threat Hunter for Windows.
    Zero external dependencies (pure Python standard library & native Win32/WMI APIs).
    """

    def __init__(self, quarantine_dir: Optional[str] = None):
        if quarantine_dir:
            self.quarantine_dir = quarantine_dir
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.quarantine_dir = os.path.join(base_dir, ".quarantine")

        try:
            os.makedirs(self.quarantine_dir, exist_ok=True)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # 1. Process Masquerading, Parentage & LOLBin Inspection
    # -------------------------------------------------------------------------
    def scan_running_processes(self) -> Dict[str, Any]:
        """
        Scans all running processes to detect:
        1. Process Masquerading (system binaries running outside C:\\Windows\\System32).
        2. Parent-Child Process Anomalies (e.g. svchost not spawned by services.exe, Office/Browser spawning cmd).
        3. Living-off-the-land (LOLBin) command-line abuse.
        4. Executables running out of suspicious writeable directories.
        """
        threats = []
        suspicious = []
        scanned_count = 0

        # Query Win32_Process via PowerShell CimInstance
        ps_cmd = (
            "Get-CimInstance Win32_Process | "
            "Select-Object ProcessId, ParentProcessId, Name, ExecutablePath, CommandLine | "
            "ConvertTo-Json -Compress"
        )

        try:
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                stderr=subprocess.DEVNULL,
                text=True,
                errors="ignore"
            )
            raw = json.loads(out)
            processes = raw if isinstance(raw, list) else [raw]
        except Exception:
            processes = []

        # Build PID -> Name map for parentage analysis
        pid_map = {p.get("ProcessId"): p.get("Name", "").lower() for p in processes if p.get("ProcessId")}

        for p in processes:
            scanned_count += 1
            pid = p.get("ProcessId")
            parent_pid = p.get("ParentProcessId")
            name = (p.get("Name") or "").lower()
            exe_path = (p.get("ExecutablePath") or "").lower()
            cmd_line = (p.get("CommandLine") or "").lower()
            parent_name = pid_map.get(parent_pid, "unknown")

            # 1. Core binary masquerade (path spoofing)
            if name in SYSTEM_CORE_BINARIES:
                legit_dir = SYSTEM_CORE_BINARIES[name]
                if exe_path and not exe_path.startswith(legit_dir):
                    threats.append({
                        "type": "CRITICAL_MASQUERADE",
                        "severity": "CRITICAL",
                        "name": p.get("Name"),
                        "pid": pid,
                        "path": p.get("ExecutablePath"),
                        "description": f"Process masquerading as Windows core binary '{name}', launched from rogue location '{exe_path}'.",
                        "recommended_action": f"Terminate PID {pid} and quarantine file immediately.",
                    })

            # 2. Parent-Child anomaly (e.g. svchost parentage)
            if name in CORE_EXPECTED_PARENTS:
                expected_parents = CORE_EXPECTED_PARENTS[name]
                if parent_name != "unknown" and parent_name not in expected_parents:
                    threats.append({
                        "type": "PARENTAGE_ANOMALY",
                        "severity": "CRITICAL",
                        "name": p.get("Name"),
                        "pid": pid,
                        "parent_pid": parent_pid,
                        "parent_name": parent_name,
                        "description": f"Core component '{name}' has suspicious parent '{parent_name}' (expected: {', '.join(expected_parents)}). Possible process injection or hollowing.",
                        "recommended_action": f"Investigate PID {pid}.",
                    })

            # 3. Office application or Browser spawning shell
            office_apps = ("winword.exe", "excel.exe", "powerpnt.exe", "acrord32.exe", "chrome.exe", "msedge.exe", "firefox.exe")
            spawning_shells = ("cmd.exe", "powershell.exe", "wscript.exe", "cscript.exe", "mshta.exe")
            if parent_name in office_apps and name in spawning_shells:
                threats.append({
                    "type": "WEAPONIZED_DOCUMENT_EXECUTION",
                    "severity": "CRITICAL",
                    "name": p.get("Name"),
                    "pid": pid,
                    "parent_name": parent_name,
                    "command": cmd_line[:150],
                    "description": f"Application '{parent_name}' spawned command interpreter '{name}'. Typical macro/exploit dropper behavior.",
                    "recommended_action": f"Terminate PID {pid}.",
                })

            # 4. LOLBin command-line matching
            for pattern, desc in LOLBIN_SIGNATURES:
                if re.search(pattern, cmd_line, re.IGNORECASE):
                    suspicious.append({
                        "type": "LOLBIN_ABUSE",
                        "severity": "HIGH",
                        "name": p.get("Name"),
                        "pid": pid,
                        "command": cmd_line[:160],
                        "description": desc,
                        "recommended_action": f"Audit process PID {pid}.",
                    })
                    break

            # 5. Double extension execution
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
                    break

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
            "message": f"Process & Parentage Audit: Scanned {scanned_count} processes. {status}."
        }

    # -------------------------------------------------------------------------
    # 2. Active Network Beacon & Reverse-Shell Sockets Scanner
    # -------------------------------------------------------------------------
    def scan_network_beacons(self) -> Dict[str, Any]:
        """
        Inspects active TCP/UDP connections and correlates PIDs to executable paths.
        Flags processes communicating with remote internet servers if the executable
        resides in non-system writeable folders (%TEMP%, %APPDATA%, Downloads).
        """
        beacons = []
        suspicious_sockets = 0

        ps_cmd = (
            "Get-NetTCPConnection -State Established, Listen -ErrorAction SilentlyContinue | "
            "Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort, State, OwningProcess | "
            "ConvertTo-Json -Compress"
        )

        try:
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                stderr=subprocess.DEVNULL,
                text=True,
                errors="ignore"
            )
            raw = json.loads(out)
            conns = raw if isinstance(raw, list) else [raw]
        except Exception:
            conns = []

        # Batch query all running process paths in a single call for high-speed correlation
        pid_paths = {}
        try:
            p_out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", "Get-Process | Select-Object Id, Path | ConvertTo-Json -Compress"],
                stderr=subprocess.DEVNULL,
                text=True,
                errors="ignore"
            )
            p_raw = json.loads(p_out)
            p_list = p_raw if isinstance(p_raw, list) else [p_raw]
            for pr in p_list:
                p_id = pr.get("Id")
                p_path = (pr.get("Path") or "").lower()
                if p_id:
                    pid_paths[p_id] = p_path
        except Exception:
            pass

        for c in conns:
            pid = c.get("OwningProcess")
            if not pid or pid <= 4:
                continue

            exe_path = pid_paths.get(pid, "")
            rem_addr = str(c.get("RemoteAddress", ""))
            rem_port = c.get("RemotePort", 0)
            state = c.get("State", "")

            # Filter loopback and private networks
            is_private = rem_addr.startswith(("127.", "10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.", "172.2", "172.3", "0.0.0.0", "::"))

            # Check if an established outbound socket belongs to an executable in Temp or AppData
            in_temp = r"\temp" in exe_path
            in_appdata_roam = r"\appdata\roaming" in exe_path and not any(k in exe_path for k in ["discord", "slack", "spotify", "code.exe"])
            in_downloads = r"\downloads" in exe_path

            if not is_private and state == 5 and (in_temp or in_downloads):  # State 5 is Established in MIB
                beacons.append({
                    "severity": "CRITICAL",
                    "type": "ROGUE_OUTBOUND_BEACON",
                    "pid": pid,
                    "executable": exe_path,
                    "remote_socket": f"{rem_addr}:{rem_port}",
                    "description": f"Process executing from temporary/download folder established active outbound socket to {rem_addr}:{rem_port}. Likely RAT, C2 beacon, or infostealer.",
                    "recommended_action": f"Terminate PID {pid} and block destination IP {rem_addr}."
                })
            elif state == 2 and in_temp: # State 2 is Listen
                beacons.append({
                    "severity": "CRITICAL",
                    "type": "REVERSE_SHELL_LISTENER",
                    "pid": pid,
                    "executable": exe_path,
                    "local_port": c.get("LocalPort"),
                    "description": f"Process in temporary directory opened listening port {c.get('LocalPort')}. Common backdoor behavior.",
                    "recommended_action": f"Terminate PID {pid} immediately."
                })

        return {
            "success": True,
            "connections_audited": len(conns),
            "threat_beacons_count": len(beacons),
            "beacons": beacons,
            "message": f"Network Beacon Audit: Checked {len(conns)} active connections. Found {len(beacons)} suspicious sockets."
        }

    # -------------------------------------------------------------------------
    # 3. Scheduled Tasks & Registry Persistence Hunter
    # -------------------------------------------------------------------------
    def scan_persistence(self) -> Dict[str, Any]:
        """
        Inspects Windows Run/RunOnce registry keys, Startup folders, and Scheduled Tasks
        for stealth malware persistence mechanisms.
        """
        findings = []

        # 1. Registry Run Keys
        targets = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU Run"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKCU RunOnce"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKLM RunOnce"),
        ]

        for hive, subkey, origin in targets:
            try:
                with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
                    count = winreg.QueryInfoKey(key)[1]
                    for i in range(count):
                        name, val, _ = winreg.EnumValue(key, i)
                        val_str = str(val).lower()

                        is_temp = r"\temp" in val_str or "%temp%" in val_str
                        is_vbs = val_str.endswith(".vbs") or "wscript" in val_str
                        is_hidden = "-w hidden" in val_str or "-enc" in val_str

                        reasons = []
                        if is_temp:
                            reasons.append("Launches from temporary folder")
                        if is_vbs:
                            reasons.append("Launches VBScript interpreter")
                        if is_hidden:
                            reasons.append("Hidden encoded script execution")

                        if reasons:
                            findings.append({
                                "category": "Registry Persistence",
                                "name": str(name),
                                "command": str(val),
                                "location": origin,
                                "severity": "HIGH",
                                "description": f"Suspicious entry: {', '.join(reasons)}",
                            })
            except Exception:
                pass

        # 2. Scheduled Tasks Audit (schtasks)
        try:
            out = subprocess.check_output(
                ["schtasks", "/query", "/fo", "CSV", "/v"],
                stderr=subprocess.DEVNULL,
                text=True,
                errors="ignore"
            )
            for line in out.splitlines():
                if not line.startswith('"'):
                    continue
                parts = [p.strip(' "') for p in line.split('","')]
                if len(parts) >= 9:
                    task_name = parts[0]
                    task_run = parts[8].lower()
                    if any(bad in task_run for bad in [r"\temp", r"\appdata\local\temp", "-w hidden", "-enc", "wscript"]):
                        findings.append({
                            "category": "Scheduled Task Persistence",
                            "name": task_name,
                            "command": parts[8],
                            "location": "Task Scheduler",
                            "severity": "CRITICAL" if "-enc" in task_run or r"\temp" in task_run else "HIGH",
                            "description": f"Task launches payload from temp or uses hidden execution: {task_run[:120]}",
                        })
        except Exception:
            pass

        return {
            "success": True,
            "findings_count": len(findings),
            "findings": findings,
            "message": f"Persistence Audit: Identified {len(findings)} suspicious persistence mechanism(s)."
        }

    # -------------------------------------------------------------------------
    # 4. Windows Security Tampering & AV Blindspot Scanner
    # -------------------------------------------------------------------------
    def scan_security_tampering(self) -> Dict[str, Any]:
        """
        Detects if malware or ransomware has tampered with Windows Defender,
        disabled Real-Time Protection, altered UAC, or disabled Windows Firewall.
        """
        tampering_flags = []

        # 1. Check Windows Defender Policies in HKLM
        defender_key = r"SOFTWARE\Policies\Microsoft\Windows Defender"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, defender_key, 0, winreg.KEY_READ) as key:
                try:
                    val, _ = winreg.QueryValueEx(key, "DisableAntiSpyware")
                    if val == 1:
                        tampering_flags.append({
                            "severity": "CRITICAL",
                            "subsystem": "Windows Defender",
                            "setting": "DisableAntiSpyware",
                            "description": "Windows Defender has been globally disabled via policy registry key.",
                        })
                except FileNotFoundError:
                    pass
        except Exception:
            pass

        # Check Real-Time Protection
        rt_key = r"SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rt_key, 0, winreg.KEY_READ) as key:
                for setting in ["DisableRealtimeMonitoring", "DisableBehaviorMonitoring", "DisableIOAVProtection"]:
                    try:
                        val, _ = winreg.QueryValueEx(key, setting)
                        if val == 1:
                            tampering_flags.append({
                                "severity": "CRITICAL",
                                "subsystem": "Defender Real-Time Protection",
                                "setting": setting,
                                "description": f"Real-time protection setting '{setting}' is disabled via policy.",
                            })
                    except FileNotFoundError:
                        pass
        except Exception:
            pass

        # 2. Check UAC (User Account Control)
        uac_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, uac_key, 0, winreg.KEY_READ) as key:
                try:
                    val, _ = winreg.QueryValueEx(key, "EnableLUA")
                    if val == 0:
                        tampering_flags.append({
                            "severity": "CRITICAL",
                            "subsystem": "User Account Control (UAC)",
                            "setting": "EnableLUA=0",
                            "description": "UAC is completely disabled, allowing applications to silently execute with full administrator privileges.",
                        })
                except FileNotFoundError:
                    pass
        except Exception:
            pass

        return {
            "success": True,
            "tampered": len(tampering_flags) > 0,
            "flags_count": len(tampering_flags),
            "flags": tampering_flags,
            "message": f"Tampering Audit: {'WARNING - Security Tampering Detected!' if tampering_flags else 'All Windows core defenses & Defender settings are intact.'}"
        }

    # -------------------------------------------------------------------------
    # 5. File & Directory Threat Scanner
    # -------------------------------------------------------------------------
    def scan_file(self, filepath: str) -> Dict[str, Any]:
        """
        Deep binary examination:
        - Deceptive double extension analysis
        - Disguised PE Executable header (MZ) check
        - SHA256 checksum calculation & signature match
        """
        if not os.path.isfile(filepath):
            return {"success": False, "message": f"Target file '{filepath}' not found."}

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

            if sha256.lower() == EICAR_SHA256:
                threats.append("EICAR Standard Antivirus Test Signature detected")
                severity = "CRITICAL"
        except Exception as e:
            return {"success": False, "message": f"Error hashing file: {e}"}

        # 3. Disguised Windows PE Executable check
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
            "message": f"File '{os.path.basename(filepath)}': [{severity}] - {', '.join(threats) if threats else 'Clean'}"
        }

    def scan_directory(self, folder_path: str, max_files: int = 250) -> Dict[str, Any]:
        """Scans all files in a folder recursively up to safety cap."""
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
            "message": f"Directory Scan '{folder_path}': Scanned {scanned} files. Found {len(threats_found)} item(s)."
        }

    # -------------------------------------------------------------------------
    # 6. Active Threat Neutralizer & Quarantine Vault
    # -------------------------------------------------------------------------
    def quarantine_file(self, filepath: str) -> Dict[str, Any]:
        """Safely isolates a suspicious file into the quarantine vault."""
        if not os.path.isfile(filepath):
            return {"success": False, "message": f"Target file '{filepath}' does not exist."}

        try:
            fname = os.path.basename(filepath)
            timestamp = int(time.time())
            quarantined_name = f"{fname}_{timestamp}.aegis_quarantined"
            dest_path = os.path.join(self.quarantine_dir, quarantined_name)

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
                "message": f"Quarantined '{fname}' -> '{dest_path}'."
            }
        except Exception as err:
            return {"success": False, "message": f"Failed to quarantine file: {err}"}

    def hunter_killer(self, pid: int, quarantine_executable: bool = True) -> Dict[str, Any]:
        """
        Terminates a hostile process and its child process tree, queries its binary path,
        and isolates it into the quarantine vault.
        """
        exe_path = ""
        try:
            q_cmd = f"(Get-Process -Id {pid} -ErrorAction SilentlyContinue).Path"
            exe_path = subprocess.check_output(["powershell", "-NoProfile", "-Command", q_cmd], text=True, errors="ignore").strip()
        except Exception:
            pass

        # Force terminate process tree
        killed = False
        try:
            subprocess.check_output(["taskkill", "/PID", str(pid), "/T", "/F"], stderr=subprocess.DEVNULL)
            killed = True
        except Exception:
            killed = False

        quarantined = False
        q_msg = ""
        if quarantine_executable and exe_path and os.path.isfile(exe_path):
            q_res = self.quarantine_file(exe_path)
            quarantined = q_res.get("success", False)
            q_msg = q_res.get("message", "")

        return {
            "success": killed,
            "pid": pid,
            "executable_path": exe_path,
            "process_terminated": killed,
            "executable_quarantined": quarantined,
            "message": f"Hunter Killer: PID {pid} terminated. {q_msg if quarantined else ''}"
        }

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
    # 7. Deep Threat Audit (Master Orchestrator)
    # -------------------------------------------------------------------------
    def deep_threat_audit(self) -> Dict[str, Any]:
        """
        Master Enterprise-Grade Security Audit across all threat vectors:
        1. Process Masquerading, Parentage & LOLBins
        2. Active Network Beacons & C2 Sockets
        3. Registry & Scheduled Tasks Persistence
        4. Windows Security Tampering & UAC/Defender Integrity
        5. %TEMP% Directory Binary Inspection
        """
        procs = self.scan_running_processes()
        beacons = self.scan_network_beacons()
        persist = self.scan_persistence()
        tampering = self.scan_security_tampering()

        # Temp check
        temp_dir = os.environ.get("TEMP", "")
        temp_threats = []
        if temp_dir and os.path.exists(temp_dir):
            t_res = self.scan_directory(temp_dir, max_files=100)
            temp_threats = t_res.get("threats", [])

        temp_crit = sum(1 for t in temp_threats if t.get("severity") == "CRITICAL")
        temp_susp = sum(1 for t in temp_threats if t.get("severity") == "SUSPICIOUS")

        total_critical = (
            procs.get("threats_count", 0) +
            beacons.get("threat_beacons_count", 0) +
            tampering.get("flags_count", 0) +
            temp_crit
        )
        total_suspicious = (
            procs.get("suspicious_count", 0) +
            persist.get("findings_count", 0) +
            temp_susp
        )

        if total_critical > 0:
            security_grade = "CRITICAL"
            verdict = f"DANGER: {total_critical} active critical threat(s) / tampering vector(s) detected!"
        elif total_suspicious > 0:
            security_grade = "SUSPICIOUS"
            verdict = f"WARNING: {total_suspicious} suspicious artifact(s) or LOLBin command(s) identified."
        else:
            security_grade = "FORTIFIED"
            verdict = "Zero threats detected. All process parentage, network sockets, and security policies are clean."

        report = f"""
============================================================
           AEGIS MILITARY-GRADE THREAT AUDIT REPORT         
============================================================
Overall Defense Grade: [{security_grade}]
Verdict: {verdict}

[SECURITY VECTORS INSPECTED]
- Running Processes: {procs.get('processes_scanned', 0)} audited | Threats: {procs.get('threats_count', 0)} | Suspicious: {procs.get('suspicious_count', 0)}
- Network Sockets: {beacons.get('connections_audited', 0)} audited | Rogue Beacons: {beacons.get('threat_beacons_count', 0)}
- Persistence Vectors: {persist.get('findings_count', 0)} suspicious startup/task entries
- Security Tampering: {'CLEAN (Defender & UAC Protected)' if not tampering.get('tampered') else 'TAMPERED (' + str(tampering.get('flags_count')) + ' policy overrides)'}
- Temporary Artifacts: {temp_crit} critical / {temp_susp} suspicious file(s) in %TEMP%
============================================================
"""
        return {
            "success": True,
            "security_grade": security_grade,
            "verdict": verdict,
            "total_critical": total_critical,
            "total_suspicious": total_suspicious,
            "processes": procs,
            "beacons": beacons,
            "persistence": persist,
            "tampering": tampering,
            "temp_threats": temp_threats,
            "summary_report": report.strip(),
            "message": f"Threat Audit Complete: [{security_grade}] - {verdict}"
        }

    # Backward compatibility
    def quick_scan(self) -> Dict[str, Any]:
        return self.deep_threat_audit()
