"""
Command Handler Module
Handles various voice commands for desktop automation and system tasks.

This version is extended for Atlas:
- Keeps all existing English commands intact (time, date, Chrome, Notepad, Google, YouTube).
- Adds bilingual / context-friendly commands that act on the currently active window.
"""

import os
import re
import shutil
import webbrowser
try:
    import pywhatkit as pwt
except Exception:
    pwt = None
from datetime import datetime
import subprocess
from typing import Optional, List

from .desktop_automation import DesktopAutomation


class CommandHandler:
    """
    A class to handle and execute various voice commands.
    """

    def __init__(self):
        """Initialize the command handler."""
        # Legacy mapping (kept for backward compatibility, not heavily used)
        self.commands = {
            "time": self.get_time,
            "date": self.get_date,
            "chrome": self.open_chrome,
            "notepad": self.open_notepad,
            "google": self.search_google,
            "youtube": self.search_youtube,
        }
        self.desktop = DesktopAutomation()
        self.active_app: Optional[str] = None
        self.active_profile: Optional[str] = None

    def _find_app_path(self, exe_names: List[str], common_full_paths: List[str] = None) -> Optional[str]:
        """Helper to find an application executable dynamically."""
        # 1. Check PATH for executable names
        for exe in exe_names:
            found = shutil.which(exe)
            if found:
                return found
        
        # 2. Check common absolute paths
        if common_full_paths:
            for raw_path in common_full_paths:
                path = os.path.expandvars(os.path.expanduser(raw_path))
                if os.path.exists(path):
                    return path
        return None

    # -------------------------------------------------------------------------
    # Internal helpers for context tracking
    # -------------------------------------------------------------------------

    def _set_active_app(self, app: Optional[str], profile: Optional[str] = None) -> None:
        """
        Update the in‑memory notion of which application Atlas is currently
        operating on. This is intentionally simple and does not depend on
        OS‑level window handles – it only reflects what Atlas last opened.
        """
        self.active_app = app
        if app == "chrome":
            self.active_profile = profile
        else:
            self.active_profile = None

    # -------------------------------------------------------------------------
    # Basic info commands (time / date)
    # -------------------------------------------------------------------------

    def get_time(self):
        """Get and return the current time."""
        now = datetime.now()
        current_time = now.strftime("%I:%M %p")  # Format: HH:MM AM/PM
        return f"The current time is {current_time}"

    def get_date(self):
        """Get and return the current date."""
        now = datetime.now()
        current_date = now.strftime("%B %d, %Y")  # Format: Month Day, Year
        return f"Today's date is {current_date}"

    # -------------------------------------------------------------------------
    # Application launchers
    # -------------------------------------------------------------------------

    def open_chrome(self):
        """Open Google Chrome browser."""
        try:
            exe_path = self._find_app_path(
                ["chrome.exe", "chrome"],
                [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    r"~\AppData\Local\Google\Chrome\Application\chrome.exe"
                ]
            )

            if exe_path:
                subprocess.Popen([exe_path])
                self._set_active_app("chrome")
                return "Opening Google Chrome"

            # Fallback: try to open with default browser
            webbrowser.open("https://www.google.com")
            return "Opening browser"
        except Exception as e:
            return f"Sorry, I couldn't open Chrome. Error: {str(e)}"

    def open_notepad(self):
        """Open Notepad application."""
        try:
            subprocess.Popen(["notepad.exe"])
            # Treat Notepad as the active editing context
            self._set_active_app("notepad")
            return "Opening Notepad"
        except Exception as e:
            return f"Sorry, I couldn't open Notepad. Error: {str(e)}"

    def close_application(self, process_name: str):
        """
        Close an application by process name using taskkill.

        This is a best-effort helper and may require appropriate permissions.
        """
        try:
            # Use subprocess.run to ensure the command executes
            result = subprocess.run(
                ["taskkill", "/IM", process_name, "/F"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            # Clear active app context if we closed the active app
            name_lower = process_name.lower()
            app_mapping = {
                "chrome.exe": "chrome",
                "notepad.exe": "notepad",
                "winword.exe": "word",
                "excel.exe": "excel",
                "powerpnt.exe": "powerpoint"
            }
            for proc, app in app_mapping.items():
                if proc in name_lower and self.active_app == app:
                    self._set_active_app(None)
                    break
            
            if result.returncode == 0:
                return f"Successfully closed {process_name}"
            else:
                # Try Alt+F4 as fallback for the active window
                if self.active_app:
                    self.desktop.close_active_window()
                    return f"Attempted to close {process_name}"
                return f"Could not close {process_name}. Process may not be running."
        except subprocess.TimeoutExpired:
            return f"Timeout while trying to close {process_name}"
        except Exception as e:
            # Fallback: try Alt+F4 to close active window
            try:
                self.desktop.close_active_window()
                return f"Closed the active window (fallback method)"
            except:
                return f"Error closing application: {str(e)}"

    def open_word(self):
        """Open Microsoft Word (best-effort path resolution)."""
        try:
            exe_path = self._find_app_path(
                ["WINWORD.EXE", "winword"],
                [
                    r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
                    r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
                    r"C:\Program Files\Microsoft Office\Office16\WINWORD.EXE",
                    r"C:\Program Files (x86)\Microsoft Office\Office16\WINWORD.EXE"
                ]
            )

            if exe_path:
                os.startfile(exe_path)
                self._set_active_app("word")
                return "Opening Microsoft Word"
            
            # Fallback
            subprocess.Popen(["start", "winword"], shell=True)
            self._set_active_app("word")
            return "Opening Microsoft Word"
        except Exception as e:
            return f"Sorry, I couldn't open Microsoft Word. Error: {e}"

    def open_excel(self):
        """Open Microsoft Excel (best-effort path resolution)."""
        try:
            exe_path = self._find_app_path(
                ["EXCEL.EXE", "excel"],
                [
                    r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
                    r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE",
                    r"C:\Program Files\Microsoft Office\Office16\EXCEL.EXE",
                    r"C:\Program Files (x86)\Microsoft Office\Office16\EXCEL.EXE"
                ]
            )

            if exe_path:
                os.startfile(exe_path)
                self._set_active_app("excel")
                return "Opening Microsoft Excel"
            
            # Fallback
            subprocess.Popen(["start", "excel"], shell=True)
            self._set_active_app("excel")
            return "Opening Microsoft Excel"
        except Exception as e:
            return f"Sorry, I couldn't open Microsoft Excel. Error: {e}"

    def open_powerpoint(self):
        """Open Microsoft PowerPoint (best-effort path resolution)."""
        try:
            exe_path = self._find_app_path(
                ["POWERPNT.EXE", "powerpnt"],
                [
                    r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
                    r"C:\Program Files (x86)\Microsoft Office\root\Office16\POWERPNT.EXE",
                    r"C:\Program Files\Microsoft Office\Office16\POWERPNT.EXE",
                    r"C:\Program Files (x86)\Microsoft Office\Office16\POWERPNT.EXE"
                ]
            )

            if exe_path:
                os.startfile(exe_path)
                self._set_active_app("powerpoint")
                return "Opening Microsoft PowerPoint"
            
            # Fallback
            subprocess.Popen(["start", "powerpnt"], shell=True)
            self._set_active_app("powerpoint")
            return "Opening Microsoft PowerPoint"
        except Exception as e:
            return f"Sorry, I couldn't open Microsoft PowerPoint. Error: {e}"

    def open_chrome_profile(self, profile_name: str):
        """
        Open Chrome with a specific profile directory.

        This assumes that the profile directory name roughly matches the
        spoken account/profile name. For example:
        - 'Default'
        - 'Profile 1'
        - 'Profile 2'
        """
        try:
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
            ]

            for path in chrome_paths:
                if os.path.exists(path):
                    # Normalize profile name (remove extra words)
                    profile = profile_name.strip().title()
                    # Launch Chrome with profile directory argument
                    subprocess.Popen([path, f"--profile-directory={profile}"])
                    # Track that Chrome with this profile is now the active context
                    self._set_active_app("chrome", profile=profile)
                    return f"Opening Chrome with profile {profile}"

            # Fallback: just open Chrome normally
            return self.open_chrome()
        except Exception as e:
            return f"Sorry, I couldn't open Chrome with that account. Error: {e}"

    # -------------------------------------------------------------------------
    # Extended desktop commands used by Atlas (additive, non-breaking)
    # -------------------------------------------------------------------------

    def open_recycle_bin(self):
        """Open the Windows Recycle Bin using the DesktopAutomation helper."""
        result = self.desktop.open_recycle_bin()
        # Set logical context so that follow‑up commands like "select everything"
        # and "delete this" feel naturally bound to the Recycle Bin window.
        self._set_active_app("recycle_bin")
        return result

    # -------------------------------------------------------------------------
    # Context‑aware helpers that build on DesktopAutomation
    # -------------------------------------------------------------------------

    def _search_selected_text_in_chrome(self) -> str:
        """
        Use the current text selection in the active Chrome window as a
        search query. This mirrors the user flow:
        - select some text
        - say "search this on Chrome"
        """
        # If we have window title access, use it for stronger context checking
        title = self.desktop.get_active_window_title()
        is_chrome_active = False
        
        if title and ("chrome" in title.lower() or "google" in title.lower()):
            is_chrome_active = True
        elif self.active_app == "chrome":
            # Fallback to logical context track if title unavailable
            is_chrome_active = True
            
        if not is_chrome_active:
            # If user explicitly said "search this on Chrome", we can try to
            # activate Chrome, but for now let's just warn or try fallback.
            return "Chrome is not the active window right now."

        selected = self.desktop.get_selected_text_from_active_window()
        if not selected:
            return (
                "No text is currently selected on screen. "
                "Please select some text first, then say 'search this on Chrome'."
            )

        return self.desktop.search_in_active_browser(selected)

    def _type_in_active_editor(self, text: str) -> str:
        """
        Route typing commands to the appropriate active editor window.
        Today this is primarily Notepad, but the helper is generic and
        simply types wherever the caret is focused.
        """
        return self.desktop.type_text_in_active_window(text)

    def _save_in_active_editor(self) -> str:
        """
        Route save commands (e.g., 'save this') to the active editor window.
        """
        return self.desktop.save_in_active_window()

    def _save_with_name_to_location(self, raw_text: str) -> Optional[str]:
        """
        Parse commands like:
        - 'save file with name report on desktop'
        - 'save file with name project report in documents'
        and delegate to DesktopAutomation.save_file_with_name.
        """
        text_lower = raw_text.lower()
        if "save file with name" not in text_lower:
            return None

        # Extract part after 'save file with name'
        after = text_lower.split("save file with name", 1)[-1].strip()

        location_hint = None
        name_part = after

        for marker in ["on desktop", "in desktop"]:
            if marker in after:
                name_part = after.split(marker, 1)[0].strip()
                location_hint = "desktop"
                break

        for marker in ["in documents", "on documents"]:
            if marker in after:
                name_part = after.split(marker, 1)[0].strip()
                location_hint = "documents"
                break

        # Clean filler words
        for filler in ["called", "named", "name", "file", "folder", "as"]:
            name_part = name_part.replace(filler, "")

        name_part = name_part.strip().strip('"').strip("'")
        if not name_part:
            return "File name was not clear. Please specify a file name."

        return self.desktop.save_file_with_name(name_part, location_hint=location_hint)

    def open_website_from_text(self, text: str):
        """
        Try to extract a website / URL-like token from free-form text and open it.

        This is intentionally simple and conservative: we look for something that
        looks like a domain name (with a dot), or we fall back to opening the
        whole text as a search query in the browser.
        """
        text = text.strip()
        # Basic URL/domain detection
        url_match = re.search(r"([a-zA-Z0-9\-]+\.[a-zA-Z]{2,})(/[^\s]*)?", text)
        if url_match:
            url = url_match.group(0)
            return self.desktop.open_website(url)
        # Fallback: treat as Google search
        return self.search_google(text)

    # -------------------------------------------------------------------------
    # Command catalog for UI (auto-generated help sidebar)
    # -------------------------------------------------------------------------

    def get_command_catalog(self):
        """
        Return a structured catalog of supported voice commands for display
        in the UI sidebar. This is kept in sync with process_command.
        """
        return [
            {
                "category": "Time & Date",
                "name": "Ask time or date",
                "description": "Get the current time or today’s date.",
                "examples": [
                    "What time is it?",
                    "What's the date today?",
                ],
            },
            {
                "category": "Browser (Chrome)",
                "name": "Open Chrome",
                "description": "Launch Google Chrome or the default browser.",
                "examples": [
                    "Open Chrome",
                    "Open Google Chrome",
                ],
            },
            {
                "category": "Browser (Chrome)",
                "name": "Open Chrome with profile",
                "description": "Launch Chrome with a specific profile/account when available.",
                "examples": [
                    "Open Chrome with Alisha profile",
                    "Open profile Alisha",
                ],
            },
            {
                "category": "Browser (Chrome)",
                "name": "Search in browser",
                "description": "Search the active browser window using your query.",
                "examples": [
                    "Search weather today in Chrome",
                    "Search AI tools in browser",
                ],
            },
            {
                "category": "Browser (Chrome)",
                "name": "Search selected text",
                "description": "Use selected screen text as a search query in Chrome.",
                "examples": [
                    "Search this on Chrome",
                    "Search selected text",
                ],
            },
            {
                "category": "Browser (Tabs)",
                "name": "New / next / previous / close tab",
                "description": "Control browser tabs with your voice.",
                "examples": [
                    "Open new tab",
                    "Next tab",
                    "Previous tab",
                    "Close this tab",
                ],
            },
            {
                "category": "Notepad & Editors",
                "name": "Open / type / save",
                "description": "Open Notepad or editors, type text, and save.",
                "examples": [
                    "Open Notepad",
                    "Type this is a test note",
                    "Save this",
                    "Save file with name report on desktop",
                ],
            },
            {
                "category": "Microsoft Office",
                "name": "Open Word / Excel / PowerPoint",
                "description": "Launch Office apps and generate demo data.",
                "examples": [
                    "Open Word",
                    "Open Excel",
                    "Generate data for 10 random people",
                ],
            },
            {
                "category": "Recycle Bin & Folders",
                "name": "Open Recycle Bin",
                "description": "Open the Windows Recycle Bin and act on it.",
                "examples": [
                    "Open Recycle Bin",
                    "Select everything",
                    "Delete everything",
                ],
            },
            {
                "category": "Files & Folders",
                "name": "Create / open folder",
                "description": "Create and open folders by spoken name or path.",
                "examples": [
                    "Create folder Projects on desktop",
                    "Open folder Downloads",
                ],
            },
            {
                "category": "Web & Apps",
                "name": "Open websites and WhatsApp Web",
                "description": "Open websites directly or via Google search.",
                "examples": [
                    "Open website youtube.com",
                    "Open WhatsApp",
                ],
            },
            {
                "category": "Window & Dialog Control",
                "name": "Close windows and confirm dialogs",
                "description": "Close the active window or press Yes/No on dialogs.",
                "examples": [
                    "Close this",
                    "Yes",
                    "No",
                ],
            },
            {
                "category": "Mouse & Scrolling",
                "name": "Scroll and click",
                "description": "Scroll the active window and click with the mouse.",
                "examples": [
                    "Scroll down",
                    "Scroll up",
                    "Click that",
                ],
            },
            {
                "category": "System Power",
                "name": "Shutdown / restart / sleep (with confirmation)",
                "description": "Request power actions that Nova will confirm before running.",
                "examples": [
                    "Shutdown",
                    "Restart",
                    "Sleep mode",
                ],
            },
        ]

    # System-level commands are intentionally separated so they can be wrapped
    # with a confirmation flow in the frontend/UI.

    def shutdown_system(self):
        """Request a system shutdown."""
        return self.desktop.shutdown()

    def restart_system(self):
        """Request a system restart."""
        return self.desktop.restart()

    def sleep_system(self):
        """Request system sleep."""
        return self.desktop.sleep()

    # -------------------------------------------------------------------------
    # Web search helpers
    # -------------------------------------------------------------------------

    def search_google(self, query):
        """
        Search Google with the given query in a new browser tab.

        Args:
            query: The search query string
        """
        try:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            # Try to open Chrome with new tab, fallback to default browser
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
            ]
            
            chrome_found = False
            for path in chrome_paths:
                if os.path.exists(path):
                    # Open Chrome with new tab
                    subprocess.Popen([path, "--new-tab", search_url])
                    chrome_found = True
                    break
            
            if not chrome_found:
                # Fallback to default browser (should open in new tab)
                webbrowser.open(search_url)
            
            return f"Opening Google search for: {query}"
        except Exception as e:
            return f"Error opening Google search: {str(e)}"

    def search_youtube(self, query):
        """
        Search YouTube with the given query.

        Args:
            query: The search query string
        """
        if pwt is None:
            return "YouTube search is not available in this environment (headless mode)."
        try:
            pwt.playonyt(query)
            return f"Searching YouTube for {query}"
        except Exception as e:
            return f"Sorry, I couldn't search YouTube. Error: {str(e)}"

    # -------------------------------------------------------------------------
    # MAIN ENTRY: process_command
    # -------------------------------------------------------------------------

    def process_command(self, text):
        """
        Process a voice command and return the response.

        Args:
            text: The recognized voice command text

        Returns:
            str: Response message or None if command not recognized
        """
        text_lower = text.lower().strip()

        # ---------------- Basic legacy commands (unchanged) ----------------

        # Check for time command
        if any(word in text_lower for word in ["time", "what time", "current time"]):
            return self.get_time()

        # Check for date command
        if any(
            word in text_lower
            for word in ["date", "what date", "today's date", "todays date"]
        ):
            return self.get_date()

        # Check for Chrome command
        if any(word in text_lower for word in ["open chrome", "open google chrome", "google chrome"]):
            return self.open_chrome()

        # Check for Notepad command
        if any(word in text_lower for word in ["open notepad", "notepad"]):
            return self.open_notepad()

        # Check for Microsoft Office applications
        if any(
            phrase in text_lower
            for phrase in ["open word", "microsoft word"]
        ):
            return self.open_word()

        if any(
            phrase in text_lower
            for phrase in ["open excel", "microsoft excel"]
        ):
            return self.open_excel()

        if any(
            phrase in text_lower
            for phrase in ["open powerpoint", "microsoft powerpoint"]
        ):
            return self.open_powerpoint()

        # Check for search commands early (but after specific app commands)
        # This handles general "search X" commands
        if "search" in text_lower:
            # Skip if it's a specific command like "search this on Chrome" (handled later)
            if not any(phrase in text_lower for phrase in [
                "search this on chrome",
                "search this in chrome",
                "search selected text",
                "search in chrome",
                "search in browser",
                "chrome search",
                "browser search",
                "search youtube",
                "youtube"
            ]):
                # Extract query after 'search' keyword
                query = None
                
                # Handle different patterns: "search for X", "search X", "search google for X"
                if "search for" in text_lower:
                    query = text_lower.split("search for", 1)[-1].strip()
                elif "search google for" in text_lower:
                    query = text_lower.split("search google for", 1)[-1].strip()
                elif "search google" in text_lower:
                    query = text_lower.split("search google", 1)[-1].strip()
                elif text_lower.startswith("search "):
                    query = text_lower.replace("search", "", 1).strip()
                
                # Clean up the query
                if query:
                    # Remove common filler words
                    for filler in ["for", "about", "the", "a", "an", "please"]:
                        if query.startswith(filler + " "):
                            query = query[len(filler):].strip()
                    
                    if query and len(query) > 0:
                        return self.search_google(query)

        # ------------- Extended commands (English only) ---------

        # Recycle Bin
        if any(
            phrase in text_lower
            for phrase in ["recycle bin", "dustbin"]
        ):
            return self.open_recycle_bin()

        # Close commands - check these BEFORE dialog confirmations
        # Check for specific app close commands first (must be exact matches)
        if "close chrome" in text_lower:
            return self.close_application("chrome.exe")
        
        if "close notepad" in text_lower:
            return self.close_application("notepad.exe")
        
        if "close word" in text_lower:
            return self.close_application("WINWORD.EXE")
        
        if "close excel" in text_lower:
            return self.close_application("EXCEL.EXE")
        
        if "close powerpoint" in text_lower:
            return self.close_application("POWERPNT.EXE")

        # Generic "close it" / "close this" / "close window" → active window close (Alt+F4)
        if any(
            phrase in text_lower
            for phrase in ["close it", "close this", "close window"]
        ):
            # Alt+F4 will close the currently focused window. Clear our
            # logical context so future commands don't keep referring to a
            # window that is no longer on screen.
            self._set_active_app(None)
            return self.desktop.close_active_window()
        
        # Standalone "close" command (only if it's the only word or with context)
        if text_lower.strip() == "close" or (text_lower.startswith("close") and len(text_lower.split()) == 1):
            # Alt+F4 will close the currently focused window
            self._set_active_app(None)
            return self.desktop.close_active_window()

        # Generic confirmation for OS-level dialogs (e.g., delete prompts).
        # These are best-effort: we simply press Enter for yes/confirm and
        # Escape for no/cancel on the currently focused dialog.
        # NOTE: This should NOT catch "yes" when there's a pending system action
        # (that's handled in the frontend), but it can handle dialog confirmations.
        if any(
            phrase in text_lower
            for phrase in ["yes", "confirm", "ok", "okay"]
        ):
            return self.desktop.confirm_active_dialog(accept=True)

        if any(
            phrase in text_lower
            for phrase in ["no", "cancel", "abort"]
        ):
            return self.desktop.confirm_active_dialog(accept=False)

        # Open Chrome with specific account/profile name
        if "open chrome with" in text_lower or "chrome profile" in text_lower:
            # Extract the part after 'with' or 'profile'
            account_part = text_lower
            if "open chrome with" in account_part:
                account_part = account_part.split("open chrome with", 1)[-1]
            elif "chrome profile" in account_part:
                account_part = account_part.split("chrome profile", 1)[-1]
            account_part = (
                account_part.replace("account", "")
                .replace("name", "")
                .replace("profile", "")
                .strip()
            )
            if account_part:
                return self.open_chrome_profile(account_part)

        # More natural profile switching while Chrome is already active, e.g.:
        # "open profile Alisha", "profile Alisha".
        if "open profile" in text_lower or "profile " in text_lower:
            profile_part = text_lower
            if "open profile" in profile_part:
                profile_part = profile_part.split("open profile", 1)[-1]
            elif "profile" in profile_part:
                profile_part = profile_part.split("profile", 1)[-1]

            for filler in ["open", "account", "name", "profile"]:
                profile_part = profile_part.replace(filler, "")
            profile_part = profile_part.strip()

            if profile_part:
                return self.open_chrome_profile(profile_part)

        # Open arbitrary website (e.g. "open youtube.com")
        if any(
            phrase in text_lower
            for phrase in [
                "open website",
                "website open",
                "site open",
                "open site",
            ]
        ):
            # Remove common boilerplate words and pass the rest
            cleaned = text_lower
            for phrase in [
                "open website",
                "website open",
                "site open",
                "open site",
            ]:
                cleaned = cleaned.replace(phrase, "")
            cleaned = cleaned.replace("please", "").strip()
            if cleaned:
                return self.open_website_from_text(cleaned)

        # Direct WhatsApp Web support: e.g. "open whatsapp"
        if "whatsapp" in text_lower:
            # Prefer keeping everything in the currently active Chrome window
            if self.active_app == "chrome":
                return self.desktop.search_in_active_browser("https://web.whatsapp.com")
            return self.desktop.open_website("web.whatsapp.com")

        # ChatGPT / AI web interface support
        if "chatgpt" in text_lower or "chat gpt" in text_lower or "open ai chat" in text_lower:
            url = "https://chatgpt.com"
            if self.active_app == "chrome":
                return self.desktop.search_in_active_browser(url)
            return self.desktop.open_website(url)

        # Active-window selection and deletion
        if any(
            phrase in text_lower
            for phrase in ["select everything", "select all"]
        ):
            return self.desktop.select_all_in_active_window()

        if any(
            phrase in text_lower
            for phrase in ["delete this", "delete everything", "delete all"]
        ):
            # If user says "delete everything", we first select-all then delete
            if "delete everything" in text_lower or "delete all" in text_lower:
                self.desktop.select_all_in_active_window()
            return self.desktop.delete_selection_in_active_window()

        # Context‑aware browser search that reuses whatever text is currently
        # selected on screen inside Chrome. Example flow:
        # 1) "open Chrome"
        # 2) User highlights text with mouse
        # 3) "search this on Chrome"
        if any(
            phrase in text_lower
            for phrase in [
                "search this on chrome",
                "search this in chrome",
                "search selected text",
            ]
        ):
            return self._search_selected_text_in_chrome()

        # Browser search based on active window
        if any(
            phrase in text_lower
            for phrase in [
                "search in chrome",
                "search in browser",
                "chrome search",
                "browser search",
            ]
        ):
            # Remove boilerplate and treat the rest as query
            cleaned = text_lower
            for phrase in [
                "search in chrome",
                "search in browser",
                "chrome search",
                "browser search",
                "search",
            ]:
                cleaned = cleaned.replace(phrase, "")
            cleaned = cleaned.replace("please", "").strip()
            if cleaned:
                return self.desktop.search_in_active_browser(cleaned)

        # ---------------------- Low-level text editing keys --------------------

        # Space insertion in any active text field
        if any(
            phrase in text_lower
            for phrase in [
                "space",
                "add space",
                "insert space",
            ]
        ) and "backspace" not in text_lower:
            return self.desktop.press_space()

        # Backspace
        if any(
            phrase in text_lower
            for phrase in [
                "backspace",
                "delete character",
                "remove character",
            ]
        ):
            return self.desktop.press_backspace()

        # Enter / new line
        if any(
            phrase in text_lower
            for phrase in [
                "enter",
                "press enter",
                "next line",
                "new line",
                "line break",
            ]
        ):
            return self.desktop.press_enter()

        # ---------------------- Notepad / editor helpers ----------------------

        # Typing into the active window (primarily Notepad / Word / etc.).
        # Examples:
        # - "type hello world"
        if "type " in text_lower:
            trigger_index = text_lower.rfind("type ")
            if trigger_index != -1:
                # Use the original text slice so we preserve casing/punctuation.
                raw_suffix = text[trigger_index:]
                cleaned_suffix = (
                    raw_suffix.replace("type ", "", 1)
                    .replace("please", "")
                    .strip()
                )
                if cleaned_suffix:
                    return self._type_in_active_editor(cleaned_suffix)

        # Create a new document in the active editor, e.g. Notepad / Word / Excel / PowerPoint.
        # NOTE: "new tab" / "open new tab" are handled in the browser tab section below.
        # Examples:
        # - "new file"
        # - "naya file"
        if any(
            phrase in text_lower
            for phrase in ["open new tab", "new tab", "new file"]
        ):
            return self.desktop.new_document_in_active_app()

        # Generate a small table of random people data inside Word/Excel.
        # Examples:
        # - "generate data for 10 random people"
        # - "insert table for 10 people"
        if any(
            phrase in text_lower
            for phrase in [
                "10 random people",
                "ten random people",
                "random people data",
                "people table",
                "insert table for 10 people",
            ]
        ):
            if self.active_app == "excel":
                return self.desktop.fill_random_people_in_excel()
            if self.active_app == "word":
                return self.desktop.fill_random_people_in_word()

        # Saving in-place within the active editor window. Examples:
        # - "save this"
        # - "save note"
        # - "save file"
        if any(
            phrase in text_lower
            for phrase in [
                "save this",
                "save it",
                "save note",
                "save file",
            ]
        ):
            return self._save_in_active_editor()

        # Save the currently open Save dialog directly on Desktop, keeping
        # whatever file name is currently present.
        if any(
            phrase in text_lower
            for phrase in ["save on desktop", "save to desktop"]
        ):
            return self.desktop.save_current_dialog_to_desktop()

        # Save with explicit name and location, e.g.
        # "save file with name report on desktop"
        if "save file with name" in text_lower:
            named_save_result = self._save_with_name_to_location(text)
            if named_save_result is not None:
                return named_save_result

        # System power commands (these should normally be gated by confirmation in UI)
        # Check for shutdown commands
        if any(
            phrase in text_lower
            for phrase in ["shutdown", "shut down", "shutdown computer", "shutdown laptop", "shut down computer", "shut down laptop"]
        ):
            return "SYSTEM_SHUTDOWN_REQUEST"

        # Check for restart commands (including "restart laptop", "restart computer", etc.)
        if any(
            phrase in text_lower
            for phrase in ["restart", "reboot", "restart laptop", "restart computer", "reboot laptop", "reboot computer"]
        ):
            return "SYSTEM_RESTART_REQUEST"

        # Check for sleep commands
        if any(
            phrase in text_lower
            for phrase in ["sleep", "sleep mode", "put to sleep", "sleep computer", "sleep laptop"]
        ):
            return "SYSTEM_SLEEP_REQUEST"

        # ---------------------- Mouse & scroll controls ----------------------

        # Scroll down / up in the active window
        if any(
            phrase in text_lower
            for phrase in [
                "scroll down",
                "page down",
            ]
        ):
            return self.desktop.scroll_down()

        if any(
            phrase in text_lower
            for phrase in [
                "scroll up",
                "page up",
            ]
        ):
            return self.desktop.scroll_up()

        # Mouse click – best-effort implementation for "click that"-style commands.
        if any(
            phrase in text_lower
            for phrase in [
                "click that",
                "click",
                "left click",
            ]
        ):
            return self.desktop.left_click()

        if any(
            phrase in text_lower
            for phrase in [
                "right click",
                "right-click",
            ]
        ):
            return self.desktop.right_click()

        # ---------------------- Browser tab control --------------------------

        if any(
            phrase in text_lower
            for phrase in ["new tab", "open new tab"]
        ):
            return self.desktop.new_tab()

        if any(
            phrase in text_lower
            for phrase in ["next tab", "switch to next tab"]
        ):
            return self.desktop.next_tab()

        if any(
            phrase in text_lower
            for phrase in ["previous tab", "switch to previous tab"]
        ):
            return self.desktop.previous_tab()

        if any(
            phrase in text_lower
            for phrase in ["close tab", "close this tab"]
        ):
            return self.desktop.close_tab()

        # ---------------------- File & folder helpers ------------------------

        # Create folder commands, e.g. "create folder Projects on desktop"
        if "create folder" in text_lower:
            after = text_lower.split("create folder", 1)[-1].strip()
            location_hint = ""

            if "on desktop" in after:
                after = after.replace("on desktop", "").strip()
                location_hint = "desktop"
            elif "in documents" in after:
                after = after.replace("in documents", "").strip()
                location_hint = "documents"

            name = after.strip().strip('"').strip("'")
            if not name:
                return "Folder name was not clear. Please specify a folder name."

            base_dir = os.path.expanduser("~")
            if location_hint == "desktop":
                base_dir = os.path.join(base_dir, "Desktop")
            elif location_hint == "documents":
                base_dir = os.path.join(base_dir, "Documents")

            full_path = os.path.join(base_dir, name)
            return self.desktop.create_folder(full_path)

        # Open folder commands, e.g. "open folder Downloads"
        if "open folder" in text_lower or "folder " in text_lower:
            folder_part = text_lower
            if "open folder" in folder_part:
                folder_part = folder_part.split("open folder", 1)[-1]
            elif "folder" in folder_part:
                folder_part = folder_part.split("folder", 1)[-1]

            for filler in ["open", "please"]:
                folder_part = folder_part.replace(filler, "")
            folder_name = folder_part.strip().strip('"').strip("'")

            if folder_name:
                base_dir = os.path.expanduser("~")
                if folder_name in ["desktop"]:
                    target = os.path.join(base_dir, "Desktop")
                elif folder_name in ["documents"]:
                    target = os.path.join(base_dir, "Documents")
                elif folder_name in ["downloads"]:
                    target = os.path.join(base_dir, "Downloads")
                else:
                    # Try as a folder under Desktop for visibility
                    target = os.path.join(base_dir, "Desktop", folder_name)
                return self.desktop.open_file_or_folder(target)

        # ---------------------- Google / YouTube search ----------------------

        # Check for YouTube search
        if "search youtube for" in text_lower or "youtube" in text_lower or "play" in text_lower:
            # Extract query after keywords
            query = text_lower
            for keyword in ["search youtube for", "play on youtube", "youtube"]:
                if keyword in query:
                    query = query.split(keyword)[-1].strip()
                    break

            # Remove common words
            query = query.replace("play", "").replace("on", "").strip()
            if query and len(query) > 2:
                return self.search_youtube(query)

        # ---------------------- Command not recognized -----------------------

        return None
