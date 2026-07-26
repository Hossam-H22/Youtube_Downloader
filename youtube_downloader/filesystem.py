"""Filesystem and OS-level side effects (creating files, opening/clearing the console)."""

import os
import subprocess
import sys


def ensure_dir(path: str) -> None:
    """Create ``path`` (and parents) if it does not already exist."""
    os.makedirs(path, exist_ok=True)


def create_text_file(lines: list[str], path: str) -> None:
    """Write ``lines`` to ``Link.txt`` inside ``path`` (creating the folder)."""
    ensure_dir(path)  # Ensure the directory exists
    file_path = os.path.join(path, 'Link.txt')  # Define the file path

    # Write the description to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        for line in lines:
            file.write(line)


def clear_console() -> None:
    """Clear the terminal, cross-platform."""
    # Clear command for Windows
    if os.name == 'nt':
        os.system('cls')
    # Clear command for Unix/Linux/Mac
    else:
        os.system('clear')


def open_folder(path: str) -> None:
    """Open ``path`` in the system file explorer, cross-platform."""
    try:
        if os.name == 'nt':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.run(['open', path])
        else:
            subprocess.run(['xdg-open', path])
    except Exception as e:
        print(f"Could not open folder: {e}")


def pick_folder() -> str:
    """Open a native "choose folder" dialog and return the selected path.

    Uses the OS-native dialog via a subprocess (same cross-platform approach as
    :func:`open_folder`), so it works from any thread — including a Flask request
    handler. Returns ``""`` if the user cancels or no dialog tool is available.
    """
    try:
        if os.name == 'nt':
            ps = (
                'Add-Type -AssemblyName System.Windows.Forms; '
                '$d = New-Object System.Windows.Forms.FolderBrowserDialog; '
                'if ($d.ShowDialog() -eq "OK") { $d.SelectedPath }'
            )
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps],
                capture_output=True, text=True,
            )
        elif sys.platform == 'darwin':
            script = 'POSIX path of (choose folder with prompt "Select download folder")'
            result = subprocess.run(
                ['osascript', '-e', script], capture_output=True, text=True,
            )
        else:
            result = subprocess.run(
                ['zenity', '--file-selection', '--directory'],
                capture_output=True, text=True,
            )
        return result.stdout.strip()
    except Exception:
        return ""
