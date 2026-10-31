import winreg


UNINSTALL_REG_PATHS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
]


def list_installed_software(query: str = "") -> dict:
    """
    Scans Windows Registry uninstall keys to list installed desktop applications,
    their versions, publishers, and installation dates.
    Optionally filters by name/query.
    """
    seen_names = set()
    installed = []
    clean_q = query.strip().lower()

    for root_hkey, subkey_path in UNINSTALL_REG_PATHS:
        try:
            with winreg.OpenKey(root_hkey, subkey_path, 0, winreg.KEY_READ) as key:
                num_subkeys, _, _ = winreg.QueryInfoKey(key)
                for i in range(num_subkeys):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name, 0, winreg.KEY_READ) as app_key:
                            try:
                                name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                            except FileNotFoundError:
                                continue

                            if not name or not isinstance(name, str):
                                continue

                            norm_name = name.strip()
                            if not norm_name or norm_name in seen_names:
                                continue

                            if clean_q and clean_q not in norm_name.lower():
                                continue

                            def get_field(k, field_name):
                                try:
                                    val, _ = winreg.QueryValueEx(k, field_name)
                                    return str(val).strip() if val else ""
                                except FileNotFoundError:
                                    return ""

                            version = get_field(app_key, "DisplayVersion")
                            publisher = get_field(app_key, "Publisher")
                            install_date = get_field(app_key, "InstallDate")
                            install_location = get_field(app_key, "InstallLocation")
                            uninstall_str = get_field(app_key, "UninstallString")

                            seen_names.add(norm_name)
                            installed.append({
                                "name": norm_name,
                                "version": version or "Unknown",
                                "publisher": publisher or "Unknown",
                                "install_date": install_date or "Unknown",
                                "location": install_location or "",
                                "uninstall_command": uninstall_str or ""
                            })
                    except Exception:
                        continue
        except Exception:
            continue

    installed.sort(key=lambda x: x["name"].lower())

    msg_summary = f"Found {len(installed)} installed application(s)"
    if clean_q:
        msg_summary += f" matching '{query}'"

    return {
        "success": True,
        "count": len(installed),
        "apps": installed,
        "message": f"{msg_summary}: {', '.join(a['name'] for a in installed[:8])}{' ...' if len(installed) > 8 else ''}"
    }


def get_app_version(app_name: str) -> dict:
    """
    Looks up the installed version of a specific application.
    """
    if not app_name or not isinstance(app_name, str):
        return {"success": False, "message": "Application name is required."}

    res = list_installed_software(app_name)
    apps = res.get("apps", [])
    if not apps:
        return {
            "success": False,
            "name": app_name,
            "version": None,
            "message": f"Application '{app_name}' not found in installed software."
        }

    clean_target = app_name.strip().lower()
    exact = next((a for a in apps if a["name"].lower() == clean_target), apps[0])

    return {
        "success": True,
        "name": exact["name"],
        "version": exact["version"],
        "publisher": exact["publisher"],
        "location": exact.get("location", ""),
        "message": f"{exact['name']} Version: {exact['version']} ({exact['publisher']})"
    }


list_installed_applications = list_installed_software
get_installed_apps = list_installed_software


def get_app_uninstall_command(app_name: str) -> dict:
    """
    Retrieves the registered uninstallation command line for an installed application.
    """
    res = list_installed_software(app_name)
    apps = res.get("apps", [])
    if not apps:
        return {"success": False, "message": f"Application '{app_name}' not found."}

    exact = apps[0]
    uninst = exact.get("uninstall_command") or exact.get("uninstall_string", "")
    if uninst:
        return {
            "success": True,
            "name": exact["name"],
            "uninstall_command": uninst,
            "uninstall_string": uninst,
            "message": f"Uninstall Command for {exact['name']}: {uninst}"
        }
    return {"success": False, "message": f"No uninstall command registered for {exact['name']}."}
