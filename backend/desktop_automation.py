"""
Desktop Automation Module

Provides higher-level helpers for common Windows desktop actions used by Atlas,
such as opening the Recycle Bin, launching websites, and performing basic
system power operations (sleep, shutdown, restart).

All functions are best-effort and wrapped in try/except so that failures never
crash the main application – they simply return an error message that can be
spoken back to the user.
"""

import os
import random
import subprocess
import time
import webbrowser
from pathlib import Path
from typing import Optional

try:
    import pyautogui
except Exception:
    pyautogui = None
try:
    import pyperclip  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pyperclip = None


class DesktopAutomation:
    """Utility class encapsulating desktop-level actions."""

    def __init__(self) -> None:
        # Avoid accidental kill-switch if mouse moves to corner
        if pyautogui:
            pyautogui.FAILSAFE = False

    def open_website(self, url: str) -> str:
        """Open the given URL in the default browser."""
        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            webbrowser.open(url)
            return f"Opening website: {url}"
        except Exception as e:
            return f"Sorry, I couldn't open the website. Error: {e}"

    def open_recycle_bin(self) -> str:
        """Open the Windows Recycle Bin."""
        try:
            # Standard shell namespace for Recycle Bin on Windows
            subprocess.Popen(["explorer", "shell:RecycleBinFolder"])
            return "Opening Recycle Bin"
        except Exception as e:
            return f"Sorry, I couldn't open the Recycle Bin. Error: {e}"

    def open_file_or_folder(self, path: str) -> str:
        """
        Open a file or folder using the default associated application.

        The path can be absolute or relative to the user's home directory.
        """
        try:
            expanded = os.path.expandvars(os.path.expanduser(path))
            resolved = str(Path(expanded).resolve())
            if not os.path.exists(resolved):
                return f"I couldn't find this path on your computer: {resolved}"
            os.startfile(resolved)
            return f"Opening {resolved}"
        except Exception as e:
            return f"Sorry, I couldn't open that path. Error: {e}"

    def create_folder(self, path: str) -> str:
        """
        Create a folder at the given path. The path can be absolute or
        relative to the user's home directory.
        """
        try:
            expanded = os.path.expandvars(os.path.expanduser(path))
            folder_path = Path(expanded).resolve()
            folder_path.mkdir(parents=True, exist_ok=True)
            return f"Created folder: {folder_path}"
        except Exception as e:
            return f"Sorry, I couldn't create that folder. Error: {e}"

    def move_path(self, source: str, destination: str) -> str:
        """Move a file or folder from source to destination."""
        try:
            import shutil

            src = Path(os.path.expandvars(os.path.expanduser(source))).resolve()
            dst = Path(os.path.expandvars(os.path.expanduser(destination))).resolve()

            if not src.exists():
                return f"I couldn't find the source path: {src}"

            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return f"Moved {src} to {dst}"
        except Exception as e:
            return f"Sorry, I couldn't move that item. Error: {e}"

    def delete_path(self, target: str) -> str:
        """Delete a file or folder (moves to Recycle Bin when possible)."""
        try:
            from send2trash import send2trash  # safer than permanent delete

            path = Path(os.path.expandvars(os.path.expanduser(target))).resolve()
            if not path.exists():
                return f"I couldn't find the path to delete: {path}"

            send2trash(str(path))
            return f"Moved {path} to Recycle Bin"
        except ImportError:
            # Fallback: permanent delete (more dangerous, so we are explicit)
            try:
                path = Path(os.path.expandvars(os.path.expanduser(target))).resolve()
                if not path.exists():
                    return f"I couldn't find the path to delete: {path}"
                if path.is_dir():
                    import shutil

                    shutil.rmtree(str(path))
                else:
                    path.unlink()
                return f"Permanently deleted {path}"
            except Exception as e:
                return f"Sorry, I couldn't delete that item. Error: {e}"
        except Exception as e:
            return f"Sorry, I couldn't delete that item. Error: {e}"

    # --- Active-window keyboard-style automation (works on whichever window is focused) ---

    def get_active_window_title(self) -> Optional[str]:
        """Get the title of the currently active window."""
        try:
            import pygetwindow as gw
            window = gw.getActiveWindow()
            if window:
                return window.title
            return None
        except Exception:
            # Fallback or if pygetwindow fails/is not installed
            return None

    def select_all_in_active_window(self) -> str:
        """Select everything in the currently active window (Ctrl+A)."""
        try:
            title = self.get_active_window_title()
            pyautogui.hotkey("ctrl", "a")
            if title:
                return f"Selecting everything in '{title}'"
            return "Selecting everything in the active window"
        except Exception as e:
            return f"Sorry, I couldn't select everything. Error: {e}"

    def delete_selection_in_active_window(self) -> str:
        """Delete the currently selected items/text (Delete key)."""
        try:
            title = self.get_active_window_title()
            pyautogui.press("delete")
            if title:
                return f"Deleting selection in '{title}'"
            return "Deleting the current selection in the active window"
        except Exception as e:
            return f"Sorry, I couldn't delete the selection. Error: {e}"

    def close_active_window(self) -> str:
        """
        Close the currently active window using the standard Alt+F4 shortcut.
        """
        try:
            title = self.get_active_window_title()
            pyautogui.hotkey("alt", "f4")
            if title:
                return f"Closing window: {title}"
            return "Closing the active window"
        except Exception as e:
            return f"Sorry, I couldn't close the active window. Error: {e}"

    def type_text_in_active_window(self, text: str) -> str:
        """
        Type the given text into the currently active window.

        This is primarily used for hands-free typing in text editors like
        Notepad, but it works anywhere the cursor is focused in a text field.

        Uses clipboard-based paste (Ctrl+V) when pyperclip is available so
        that Unicode / Urdu text is fully supported.  Falls back to
        pyautogui.typewrite for ASCII-only environments.
        """
        try:
            if not text:
                return "No text provided to type in the active window"
            if pyperclip is not None:
                pyperclip.copy(text)
                time.sleep(0.05)
                pyautogui.hotkey("ctrl", "v")
            else:
                pyautogui.typewrite(text)
            return f"Typing in the active window: {text}"
        except Exception as e:
            return f"Sorry, I couldn't type in the active window. Error: {e}"

    def save_in_active_window(self) -> str:
        """
        Trigger a save operation in the currently active window (Ctrl+S).

        This maps naturally to editors like Notepad and many other apps.
        """
        try:
            pyautogui.hotkey("ctrl", "s")
            return "Saving in the active window"
        except Exception as e:
            return f"Sorry, I couldn't save in the active window. Error: {e}"

    def press_space(self) -> str:
        """Press a single Space key in the active window."""
        try:
            pyautogui.press("space")
            return "Pressed space in the active window"
        except Exception as e:
            return f"Sorry, I couldn't press space. Error: {e}"

    def press_backspace(self, times: int = 1) -> str:
        """Press Backspace one or more times in the active window."""
        try:
            times = max(1, min(times, 10))
            for _ in range(times):
                pyautogui.press("backspace")
            return f"Pressed backspace {times} time(s) in the active window"
        except Exception as e:
            return f"Sorry, I couldn't press backspace. Error: {e}"

    def press_enter(self, times: int = 1) -> str:
        """Press Enter one or more times in the active window."""
        try:
            times = max(1, min(times, 5))
            for _ in range(times):
                pyautogui.press("enter")
            return f"Pressed enter {times} time(s) in the active window"
        except Exception as e:
            return f"Sorry, I couldn't press enter. Error: {e}"

    def get_selected_text_from_active_window(self) -> Optional[str]:
        """
        Best-effort helper to read the currently selected text from the
        active window using the clipboard (Ctrl+C).

        Returns the captured text, or None if unavailable.
        """
        try:
            if pyperclip is None:
                return None

            # Copy current selection to clipboard
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.15)  # give the OS a moment to update clipboard
            text = pyperclip.paste()

            if isinstance(text, str):
                cleaned = text.strip()
                return cleaned or None
            return None
        except Exception:
            # We keep this silent to avoid spamming logs; callers can fall back.
            return None

    def confirm_active_dialog(self, accept: bool) -> str:
        """
        Best-effort helper to respond to the currently active confirmation
        dialog (e.g., Yes/No, OK/Cancel).

        We avoid any window-handle logic and simply simulate the most common
        keyboard shortcuts:
        - Accept: Enter (often mapped to Yes/OK)
        - Reject: Escape (often mapped to No/Cancel)
        """
        try:
            if accept:
                pyautogui.press("enter")
                return "Confirming the active dialog"
            pyautogui.press("esc")
            return "Dismissing the active dialog"
        except Exception as e:
            return f"Sorry, I couldn't interact with the dialog. Error: {e}"

    def search_in_active_browser(self, query: str) -> str:
        """
        Perform a simple search in the currently active browser window.

        Implementation:
        - Ctrl+L to focus the address bar
        - Paste the query (clipboard for Unicode support)
        - Press Enter
        """
        try:
            if not query:
                return "No query provided for searching in the active browser"

            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.1)
            if pyperclip is not None:
                pyperclip.copy(query)
                time.sleep(0.05)
                pyautogui.hotkey("ctrl", "v")
            else:
                pyautogui.typewrite(query)
            time.sleep(0.1)
            pyautogui.press("enter")
            return f"Searching in the active browser window: {query}"
        except Exception as e:
            return f"Sorry, I couldn't search in the browser. Error: {e}"

    # --- Application/editor helpers for new documents and Save As flows ------

    def new_document_in_active_app(self) -> str:
        """
        Create a new document/tab in the currently active application.

        For most editors (including the new Windows Notepad and Office apps),
        Ctrl+N either opens a new tab or a new document window.
        """
        try:
            pyautogui.hotkey("ctrl", "n")
            return "Creating a new document in the active window"
        except Exception as e:
            return f"Sorry, I couldn't create a new document. Error: {e}"

    def save_file_with_name(self, name: str, location_hint: Optional[str] = None) -> str:
        """
        Save the current document with a specific name and (optionally) a
        specific location such as the Desktop.

        Implementation (best-effort, app-agnostic):
        - Ctrl+Shift+S to open 'Save As' (works in many apps; if it opens a
          normal Save dialog that's fine too).
        - Type the full path (e.g. Desktop\\report) into the filename box.
        - Press Enter.
        """
        try:
            if not name:
                return "No file name provided to save."

            # Basic sanitisation: remove quotes that often come from speech.
            safe_name = name.replace('"', "").replace("'", "").strip()
            if not safe_name:
                return "File name was empty after cleaning, boss."

            # Resolve a simple destination path
            user_home = Path(os.path.expanduser("~"))
            location_hint_lower = (location_hint or "").lower()

            if "desktop" in location_hint_lower:
                base_dir = user_home / "Desktop"
            elif "documents" in location_hint_lower:
                base_dir = user_home / "Documents"
            else:
                # Default to Desktop for visibility
                base_dir = user_home / "Desktop"

            base_dir.mkdir(parents=True, exist_ok=True)
            target_path = base_dir / safe_name

            # Trigger Save As and type the full path
            pyautogui.hotkey("ctrl", "shift", "s")
            time.sleep(0.5)
            pyautogui.typewrite(str(target_path))
            time.sleep(0.2)
            pyautogui.press("enter")

            return f"Saving file as {target_path}"
        except Exception as e:
            return f"Sorry, I couldn't save the file with that name. Error: {e}"

    def save_current_dialog_to_desktop(self) -> str:
        """
        When a Save / Save As dialog is already open, move its target folder
        to the Desktop and confirm the save using only keyboard shortcuts.
        """
        try:
            user_home = Path(os.path.expanduser("~"))
            desktop_dir = user_home / "Desktop"
            desktop_dir.mkdir(parents=True, exist_ok=True)

            # Focus the path / address bar inside the dialog and type Desktop path
            pyautogui.hotkey("alt", "d")
            time.sleep(0.3)
            pyautogui.typewrite(str(desktop_dir))
            time.sleep(0.2)
            pyautogui.press("enter")
            time.sleep(0.4)

            # Confirm Save (Enter is usually mapped to the primary Save button)
            pyautogui.press("enter")
            return f"Saving the current file to Desktop: {desktop_dir}"
        except Exception as e:
            return f"Sorry, I couldn't save on Desktop. Error: {e}"

    # --- Simple Office automation helpers for random data --------------------

    def fill_random_people_in_excel(self, count: int = 10) -> str:
        """
        Generate and type a small table of random people into the active Excel
        sheet starting from the currently focused cell.

        Columns: Name | Age | Number
        """
        try:
            headers = ["Name", "Age", "Number"]
            # Header row
            for i, h in enumerate(headers):
                pyautogui.typewrite(h)
                if i < len(headers) - 1:
                    pyautogui.press("tab")
            pyautogui.press("enter")
            time.sleep(0.1)

            first_names = ["Ali", "Sara", "Ahmed", "Fatima", "Usman", "Alisha", "Hassan", "Zara"]
            last_names = ["Khan", "Saeed", "Malik", "Sheikh", "Siddiqui", "Hussain"]

            for _ in range(count):
                name = f"{random.choice(first_names)} {random.choice(last_names)}"
                age = str(random.randint(18, 60))
                number = "03" + "".join(str(random.randint(0, 9)) for _ in range(9))

                row = [name, age, number]
                for i, value in enumerate(row):
                    pyautogui.typewrite(value)
                    if i < len(row) - 1:
                        pyautogui.press("tab")
                pyautogui.press("enter")
                time.sleep(0.05)

            return "Filled Excel sheet with random data for 10 people"
        except Exception as e:
            return f"Sorry, I couldn't fill Excel with random people data. Error: {e}"

    def fill_random_people_in_word(self, count: int = 10) -> str:
        """
        Generate and type a simple table-like structure of random people into
        Word at the current caret location using tabs and newlines.
        """
        try:
            first_names = ["Ali", "Sara", "Ahmed", "Fatima", "Usman", "Alisha", "Hassan", "Zara"]
            last_names = ["Khan", "Saeed", "Malik", "Sheikh", "Siddiqui", "Hussain"]

            lines = ["Name\tAge\tNumber"]
            for _ in range(count):
                name = f"{random.choice(first_names)} {random.choice(last_names)}"
                age = str(random.randint(18, 60))
                number = "03" + "".join(str(random.randint(0, 9)) for _ in range(9))
                lines.append(f"{name}\t{age}\t{number}")

            table_text = "\n".join(lines)
            pyautogui.typewrite(table_text)
            return "Inserted random people table into Word"
        except Exception as e:
            return f"Sorry, I couldn't insert random people data in Word. Error: {e}"

    def add_powerpoint_slide(self) -> str:
        """
        Add a new slide in PowerPoint using the common Ctrl+M shortcut.
        """
        try:
            pyautogui.hotkey("ctrl", "m")
            return "Adding a new slide in PowerPoint"
        except Exception as e:
            return f"Sorry, I couldn't add a new slide. Error: {e}"

    # --- Mouse and scroll helpers for screen-aware control --------------------

    def scroll_down(self, amount: int = 800) -> str:
        """Scroll down in the active window by a reasonable amount."""
        try:
            pyautogui.scroll(-abs(amount))
            return "Scrolled down in the active window"
        except Exception as e:
            return f"Sorry, I couldn't scroll down. Error: {e}"

    def scroll_up(self, amount: int = 800) -> str:
        """Scroll up in the active window by a reasonable amount."""
        try:
            pyautogui.scroll(abs(amount))
            return "Scrolled up in the active window"
        except Exception as e:
            return f"Sorry, I couldn't scroll up. Error: {e}"

    def left_click(self) -> str:
        """
        Perform a left mouse click at the current cursor position.

        This is the best-effort implementation for commands like
        "click that" or "isko click karo" – Nova assumes you have
        already placed the mouse over the target.
        """
        try:
            pyautogui.click()
            return "Clicked at the current mouse position"
        except Exception as e:
            return f"Sorry, I couldn't click. Error: {e}"

    def right_click(self) -> str:
        """Perform a right mouse click at the current cursor position."""
        try:
            pyautogui.rightClick()
            return "Right-clicked at the current mouse position"
        except Exception as e:
            return f"Sorry, I couldn't right-click. Error: {e}"

    # --- Browser tab helpers (Chrome/Edge) -----------------------------------

    def new_tab(self) -> str:
        """Open a new browser tab in the active window (Ctrl+T)."""
        try:
            pyautogui.hotkey("ctrl", "t")
            return "Opening a new browser tab"
        except Exception as e:
            return f"Sorry, I couldn't open a new tab. Error: {e}"

    def close_tab(self) -> str:
        """Close the current browser tab (Ctrl+W)."""
        try:
            pyautogui.hotkey("ctrl", "w")
            return "Closing the current browser tab"
        except Exception as e:
            return f"Sorry, I couldn't close the tab. Error: {e}"

    def next_tab(self) -> str:
        """Switch to the next browser tab (Ctrl+Tab)."""
        try:
            pyautogui.hotkey("ctrl", "tab")
            return "Switching to the next browser tab"
        except Exception as e:
            return f"Sorry, I couldn't switch to the next tab. Error: {e}"

    def previous_tab(self) -> str:
        """Switch to the previous browser tab (Ctrl+Shift+Tab)."""
        try:
            pyautogui.hotkey("ctrl", "shift", "tab")
            return "Switching to the previous browser tab"
        except Exception as e:
            return f"Sorry, I couldn't switch to the previous tab. Error: {e}"

    # --- System power operations (to be triggered only after confirmation) ---

    def shutdown(self) -> str:
        """Shut down the computer immediately."""
        try:
            # Use subprocess.run to ensure command executes
            subprocess.run(["shutdown", "/s", "/t", "0"], shell=True, check=False)
            return "Shutting down the computer now"
        except Exception as e:
            return f"Error shutting down computer: {str(e)}"

    def restart(self) -> str:
        """Restart the computer immediately."""
        try:
            # Use subprocess.run to ensure command executes
            subprocess.run(["shutdown", "/r", "/t", "0"], shell=True, check=False)
            return "Restarting the computer now"
        except Exception as e:
            return f"Error restarting computer: {str(e)}"

    def sleep(self) -> str:
        """Put the computer to sleep."""
        try:
            # Use Windows API via ctypes
            import ctypes

            ctypes.windll.PowrProf.SetSuspendState(False, True, True)
            return "Putting the computer to sleep"
        except Exception as e:
            return f"Sorry, I couldn't put the computer to sleep. Error: {e}"

