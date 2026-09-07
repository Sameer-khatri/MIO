# System Agent

The MIO System Agent handles safe local Windows tasks. It finds applications and files, performs approved operations, checks the result, and reports what happened.

It is a specialist worker. It is not the MIO Brain and does not handle general reasoning, conversation context, planning, voice, or task orchestration.

## Current Status

The agent currently supports application, process, filesystem, system, port, network, and window operations.

The full test suite currently passes **105 tests**. Many Windows API and command tests use mocks. Real results still depend on the Windows desktop, installed applications, permissions, and available Windows tools.

## Responsibilities

The System Agent is responsible for:

- Finding and checking application, file, folder, and window targets.
- Checking saved targets before using them.
- Performing safe local operations.
- Reading current process, resource, port, network, and window state.
- Checking the real result after an operation when possible.
- Returning clear messages and structured results.

The MIO Brain is a separate layer. It will handle context, planning, policy, approvals, task state, and routing.

## Architecture

From the `mio` repository root:

```text
agents/system_agent/
├── agent.py
├── app_memory.json          # local machine memory; ignored by Git
├── tools/
│   ├── applications.py
│   ├── filesystem.py
│   ├── network.py
│   ├── ports.py
│   ├── processes.py
│   ├── system_info.py
│   └── windows.py
└── tests/
    └── test_system_agent.py
```

- [`agent.py`](agent.py) parses commands and runs the terminal loop.
- [`applications.py`](tools/applications.py) discovers, opens, closes, and restarts applications. It also manages aliases and saved application records.
- [`processes.py`](tools/processes.py) finds visible applications, checks running state, matches runtime identities, and sends graceful close requests.
- [`filesystem.py`](tools/filesystem.py) finds, lists, creates, copies, moves, renames, and deletes files and folders.
- [`system_info.py`](tools/system_info.py) reads CPU, RAM, disk, and GPU information.
- [`ports.py`](tools/ports.py) reads TCP and UDP port information.
- [`network.py`](tools/network.py) reads local network, Wi-Fi, connectivity, and ping information.
- [`windows.py`](tools/windows.py) finds visible windows and controls their basic state.
- [`tests/test_system_agent.py`](tests/test_system_agent.py) contains the unittest suite.

`app_memory.json` stores machine-specific paths, application targets, aliases, and verification times. It is ignored by [`.gitignore`](../../.gitignore) and must stay local to each machine.

## Capabilities

### Applications and processes

Applications can be found through saved records, built-in entries, PATH, Start Menu shortcuts, registry App Paths, and packaged Windows apps.

The agent can:

- Open an application.
- List visible running applications.
- Check whether an application is running.
- Close an application with a normal `WM_CLOSE` request.
- Restart an application after checking that it closed.

It does not kill processes. An application with unsaved work may remain open while it waits for its own confirmation dialog.

Runtime names are shared across aliases and launcher names. For example, `calc`, `calculator`, and `CalculatorApp.exe` can resolve to Calculator.

### Files and folders

The agent can list, find, create, copy, move, rename, and delete files and folders. Copy, move, and rename do not overwrite an existing target.

Friendly locations include:

`desktop`, `downloads`, `documents`, `pictures`, `videos`, `music`, and `home`.

Deletion uses the Windows Recycle Bin.

### System, ports, and network

The agent can read:

- System facts, CPU, RAM, disk, GPU information, and GPU usage.
- TCP/UDP port usage and listening ports.
- Network adapters, local IP addresses, Wi-Fi state, internet connectivity, and ping results.

These network and inspection operations do not change system or network settings.

### Windows

The agent can find visible top-level windows and report their title and state: normal, minimized, or maximized.

It can:

- List an application's windows.
- Minimize one selected window.
- Maximize one selected window.
- Restore one selected window.
- Bring one selected window to the foreground.

When there are multiple windows, the current foreground window is preferred. Otherwise, the first matching window returned by Windows is used. Window handles, titles, and states are temporary and are not saved in memory.

## Execution and Verification

Operations follow this pattern:

```text
UNDERSTAND → RESOLVE TARGET → CHECK SAFETY → ACT → VERIFY REALITY → REPORT
```

Examples:

- Saved paths, shortcuts, executables, and packaged AppIDs are checked before use.
- Ambiguous targets and existing destination names are rejected.
- Copy, move, rename, and delete check the filesystem after the operation.
- Graceful close sends `WM_CLOSE` and checks fresh window state several times.
- Minimize and maximize check `IsIconic()` or `IsZoomed()` after the request.
- Foreground control checks `GetForegroundWindow()` after `SetForegroundWindow()`.

A successful API call is not enough to report success. The agent reports success only after the available real state supports it.

## Safety

The agent includes these protections:

- Saved memory is treated as a cache. Stale paths, shortcuts, executables, and AppIDs are removed or rediscovered.
- Duplicate application records are merged into one record with aliases.
- System, session, security, Explorer, MIO-host, and other protected processes cannot be closed.
- Protected system paths, user-root paths, repository paths, and `.git` paths cannot be deleted.
- Project-like folders require confirmation before deletion.
- Deleted items are sent to the Recycle Bin and checked afterward.
- Ambiguous source and destination matches are not chosen at random.
- Folder copy and move cannot target the folder itself or one of its children.
- Window commands do not open an application that is not running.
- Windows may refuse foreground activation. The agent reports that failure instead of pretending it worked.
- Ping input is checked and passed as arguments, not as an unrestricted shell string.

## Supported Commands or API

The command entry point is `handle_command()` in [`agent.py`](agent.py). Start the interactive agent from the `mio` repository root with:

```powershell
python agents/system_agent/agent.py
```

Examples:

```text
open chrome
where is chrome
show running apps
is calculator running?
close notepad
restart chrome

minimize chrome
maximize chrome
restore chrome
bring chrome to front
bring chrome forward
switch to chrome
show windows for chrome
list windows for chrome

show system info
show cpu usage
show ram usage
show disk space
show gpu info
show gpu usage
show listening ports
what is using port 8080
is port 8080 free
show network info
show ip address
show wifi info
am i connected to internet?
ping example.com

show files in downloads
find report.pdf
create folder reports in documents
copy report.pdf to desktop
move report.pdf to documents
rename report.pdf to final_report
delete report.pdf
```

Tool functions return Python dictionaries with status, names, paths, states, matches, and messages. They are internal APIs, not a network service.

## Setup and Requirements

- Windows is required for the full feature set.
- Use a Python version that supports the `str | None` type syntax.
- The agent uses only the Python standard library. There is no System Agent requirements file or package-install command in this repository.
- Windows features used include `user32`, `kernel32`, and `shell32` through `ctypes`, PowerShell, `tasklist`, `where.exe`, `netsh`, registry access, and packaged-app discovery.
- Run commands from the `mio` repository root.

## Testing

Run the full suite from the `mio` repository root:

```powershell
python -m unittest discover -s agents\system_agent\tests -v
```

Verified result: **105 tests passed**.

The tests cover application discovery, memory checks, aliases, packaged apps, process state, graceful close and restart, filesystem safety, system information, ports, network tools, windows, protected targets, verification, and command routing.

## Known Boundaries

The agent does not include:

- Force-kill, `taskkill`, `TerminateProcess`, or arbitrary process termination.
- Arbitrary user-created PowerShell or shell commands. Internal tools use fixed Windows commands where needed.
- Mouse or keyboard automation, Alt+Tab, clipboard control, custom window positions, resizing, snapping, or multi-monitor placement.
- Screenshots, vision, GUI rendering, or voice control.
- Network configuration changes.
- An LLM, the MIO Brain, general planning, or autonomous task execution.
- Permanent storage of live process state, HWNDs, foreground state, window titles, coordinates, or resource samples.

## Integration with MIO Brain

**Planned architecture, not current functionality.**

The future MIO Brain will send validated system actions to this agent. The Brain will handle context, planning, policy, approvals, and overall task state.

The System Agent will keep its own safety checks, target resolution, Windows-specific operations, and result verification. This repository does not currently contain that Brain integration.

## Development Rules

- Add new local-system capabilities as focused tools within the System Agent.
- Put system operations in tool modules and command routing in `agent.py`.
- Keep the System Agent focused on safe, verifiable local operations.
- Recheck saved memory before using it.
- Add safety, failure, ambiguity, and verification tests for every new operation.
- Never commit machine-specific runtime memory.
