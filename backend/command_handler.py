"""
Command Handler Module
Handles various voice commands for desktop automation and system tasks.

This version is extended for Atlas:
- Keeps all existing English commands intact (time, date, Chrome, Notepad, Google, YouTube).
- Adds bilingual / context-friendly commands that act on the currently active window.
"""

import os
import re
import webbrowser
import pywhatkit as pwt
from datetime import datetime
import subprocess
from typing import Optional

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
        # Lightweight in-memory context about which app/window Atlas last
        # explicitly opened for the user. This enables natural follow-up
        # commands like "search this on Chrome" or "save this" in Notepad
        # without the user having to repeat the application name.
        #
        # Values are simple identifiers such as:
        # - "chrome"
        # - "notepad"
        # - "recycle_bin"
        self.active_app: Optional[str] = None
        # Optional extra details (e.g. active Chrome profile name)
        self.active_profile: Optional[str] = None

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
            # Try different Chrome paths on Windows
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
            ]

            for path in chrome_paths:
                if os.path.exists(path):
                    os.startfile(path)
                    # Remember that Chrome is now the active application context
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
            os.system("notepad.exe")
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
            subprocess.Popen(["taskkill", "/IM", process_name, "/F"], shell=True)
            # If we just closed the app that Atlas believed was active,
            # clear the in‑memory context so follow‑ups don't target it.
            name_lower = process_name.lower()
            if self.active_app == "chrome" and "chrome" in name_lower:
                self._set_active_app(None)
            elif self.active_app == "notepad" and "notepad" in name_lower:
                self._set_active_app(None)
            return f"Closing application: {process_name}"
        except Exception as e:
            return f"Sorry, I couldn't close {process_name}. Error: {e}"

    def open_word(self):
        """Open Microsoft Word (best-effort path resolution)."""
        try:
            # Common installation paths for Office 365 / 2019+; fall back to 'start winword'
            word_paths = [
                r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
                r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
            ]
            for path in word_paths:
                if os.path.exists(path):
                    os.startfile(path)
                    self._set_active_app("word")
                    return "Opening Microsoft Word"

            subprocess.Popen(["start", "winword"], shell=True)
            self._set_active_app("word")
            return "Opening Microsoft Word"
        except Exception as e:
            return f"Sorry, I couldn't open Microsoft Word. Error: {e}"

    def open_excel(self):
        """Open Microsoft Excel (best-effort path resolution)."""
        try:
            excel_paths = [
                r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
                r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE",
            ]
            for path in excel_paths:
                if os.path.exists(path):
                    os.startfile(path)
                    self._set_active_app("excel")
                    return "Opening Microsoft Excel"

            subprocess.Popen(["start", "excel"], shell=True)
            self._set_active_app("excel")
            return "Opening Microsoft Excel"
        except Exception as e:
            return f"Sorry, I couldn't open Microsoft Excel. Error: {e}"

    def open_powerpoint(self):
        """Open Microsoft PowerPoint (best-effort path resolution)."""
        try:
            ppt_paths = [
                r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
                r"C:\Program Files (x86)\Microsoft Office\root\Office16\POWERPNT.EXE",
            ]
            for path in ppt_paths:
                if os.path.exists(path):
                    os.startfile(path)
                    self._set_active_app("powerpoint")
                    return "Opening Microsoft PowerPoint"

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
        if self.active_app != "chrome":
            return "Chrome is not the active window right now."

        selected = self.desktop.get_selected_text_from_active_window()
        if not selected:
            return (
                "Boss, mujhe screen se koi selected text nahi mila. "
                "Please pehle text select karen phir dobara bolen "
                "'search this on Chrome'."
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

        for marker in ["on desktop", "in desktop", "desktop pe"]:
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
            return "Boss, mujhe file ka naam samajh nahi aaya."

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
                    "Chrome par weather today search karo",
                    "Browser pe AI tools search karo",
                ],
            },
            {
                "category": "Browser (Chrome)",
                "name": "Search selected text",
                "description": "Use selected screen text as a search query in Chrome.",
                "examples": [
                    "Search this on Chrome",
                    "Isko Chrome pe search karo",
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
                    "Sab select karo",
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
                    "WhatsApp open karo",
                ],
            },
            {
                "category": "Window & Dialog Control",
                "name": "Close windows and confirm dialogs",
                "description": "Close the active window or press Yes/No on dialogs.",
                "examples": [
                    "Close this",
                    "Yes",
                    "Nahi",
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
        Search Google with the given query.

        Args:
            query: The search query string
        """
        try:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(search_url)
            return f"Searching Google for {query}"
        except Exception as e:
            return f"Sorry, I couldn't search Google. Error: {str(e)}"

    def search_youtube(self, query):
        """
        Search YouTube with the given query.

        Args:
            query: The search query string
        """
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
        if any(word in text_lower for word in ["open chrome", "chrome", "google chrome"]):
            return self.open_chrome()

        # Check for Notepad command
        if any(word in text_lower for word in ["open notepad", "notepad"]):
            return self.open_notepad()

        # Check for Microsoft Office applications
        if any(
            phrase in text_lower
            for phrase in ["open word", "microsoft word", "word khol do", "word kholo"]
        ):
            return self.open_word()

        if any(
            phrase in text_lower
            for phrase in ["open excel", "microsoft excel", "excel khol do", "excel kholo"]
        ):
            return self.open_excel()

        if any(
            phrase in text_lower
            for phrase in ["open powerpoint", "powerpoint khol do", "power point kholo"]
        ):
            return self.open_powerpoint()

        # ------------- Extended commands (bilingual-ish heuristics) ---------

        # Recycle Bin (English + a bit of Roman Urdu)
        if any(
            phrase in text_lower
            for phrase in ["recycle bin", "dustbin", "kooda", "kora dan", "kooday ka dabba"]
        ):
            return self.open_recycle_bin()

        # Generic confirmation for OS-level dialogs (e.g., delete prompts).
        # These are best-effort: we simply press Enter for yes/confirm and
        # Escape for no/cancel on the currently focused dialog.
        if any(
            phrase in text_lower
            for phrase in ["yes", "haan", "han", "confirm", "ok karo", "theek hai"]
        ):
            return self.desktop.confirm_active_dialog(accept=True)

        if any(
            phrase in text_lower
            for phrase in ["no", "nahi", "nahin", "cancel", "mat karo"]
        ):
            return self.desktop.confirm_active_dialog(accept=False)

        # Close Chrome / Notepad (simple process-based close)
        if any(
            phrase in text_lower
            for phrase in ["close chrome", "band karo chrome", "chrome band karo"]
        ):
            return self.close_application("chrome.exe")
        if any(
            phrase in text_lower
            for phrase in ["close notepad", "notepad band karo", "band karo notepad"]
        ):
            return self.close_application("notepad.exe")

        # Generic "close it" / "close this" → active window close (Alt+F4)
        if any(
            phrase in text_lower
            for phrase in ["close it", "close this", "isko band karo", "ye band karo"]
        ):
            # Alt+F4 will close the currently focused window. Clear our
            # logical context so future commands don't keep referring to a
            # window that is no longer on screen.
            self._set_active_app(None)
            return self.desktop.close_active_window()

        # Open Chrome with specific account/profile name
        if "open chrome with" in text_lower or "chrome is account se kholo" in text_lower:
            # Extract the part after 'with' or 'se'
            account_part = text_lower
            if "open chrome with" in account_part:
                account_part = account_part.split("open chrome with", 1)[-1]
            elif "chrome is account se kholo" in account_part:
                account_part = account_part.split("chrome is account se kholo", 1)[-1]
            account_part = (
                account_part.replace("account", "")
                .replace("name", "")
                .replace("profile", "")
                .strip()
            )
            if account_part:
                return self.open_chrome_profile(account_part)

        # More natural profile switching while Chrome is already active, e.g.:
        # "open profile Alisha", "profile Alisha Sajjad open karo".
        if "open profile" in text_lower or "profile " in text_lower:
            profile_part = text_lower
            if "open profile" in profile_part:
                profile_part = profile_part.split("open profile", 1)[-1]
            elif "profile" in profile_part:
                profile_part = profile_part.split("profile", 1)[-1]

            for filler in ["open", "karo", "kholo", "account", "name", "profile"]:
                profile_part = profile_part.replace(filler, "")
            profile_part = profile_part.strip()

            if profile_part:
                return self.open_chrome_profile(profile_part)

        # Open arbitrary website (e.g. "open youtube.com", "is website ko open karo")
        if any(
            phrase in text_lower
            for phrase in [
                "open website",
                "website open",
                "site open",
                "site kholo",
                "website kholo",
            ]
        ):
            # Remove common boilerplate words and pass the rest
            cleaned = text_lower
            for phrase in [
                "open website",
                "website open",
                "site open",
                "website kholo",
                "site kholo",
            ]:
                cleaned = cleaned.replace(phrase, "")
            cleaned = cleaned.replace("please", "").replace("karo", "").replace(
                "karen", ""
            ).strip()
            if cleaned:
                return self.open_website_from_text(cleaned)

        # Direct WhatsApp Web support: e.g. "whatsapp open karo", "open whatsapp".
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
            for phrase in ["select everything", "select all", "sab select karo"]
        ):
            return self.desktop.select_all_in_active_window()

        if any(
            phrase in text_lower
            for phrase in ["delete this", "ye delete karo", "delete everything", "sab delete karo"]
        ):
            # If user says "delete everything", we first select-all then delete
            if "delete everything" in text_lower or "sab delete karo" in text_lower:
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
                "isko chrome pe search karo",
                "isko chrome par search karo",
            ]
        ):
            return self._search_selected_text_in_chrome()

        # Browser search based on active window
        if any(
            phrase in text_lower
            for phrase in [
                "chrome par",
                "chrome pe",
                "browser par",
                "browser pe",
                "chrome par ye search karo",
                "chrome par search karo",
                "google par ye search karo",
                "google pe ye search karo",
            ]
        ):
            # Remove boilerplate and treat the rest as query
            cleaned = text_lower
            for phrase in [
                "chrome par ye search karo",
                "chrome par search karo",
                "chrome par",
                "chrome pe",
                "browser par",
                "browser pe",
                "google par ye search karo",
                "google pe ye search karo",
                "search karo",
            ]:
                cleaned = cleaned.replace(phrase, "")
            cleaned = cleaned.replace("please", "").replace("boss", "").strip()
            if cleaned:
                return self.desktop.search_in_active_browser(cleaned)

        # ---------------------- Low-level text editing keys --------------------

        # Space insertion in any active text field. Allow many fuzzy phrases:
        # "thoda space add karo", "yahaan space do", "ek space", etc.
        if any(
            phrase in text_lower
            for phrase in [
                "thoda space",
                "space add",
                "space do",
                "space dedo",
                "yahaan space",
                "yahan space",
                "ek space",
            ]
        ) or ((" space" in text_lower or "space " in text_lower) and "backspace" not in text_lower):
            return self.desktop.press_space()

        # Backspace: "ek backspace", "thoda peeche jao", "peeche hatao", etc.
        if any(
            phrase in text_lower
            for phrase in [
                "backspace",
                "ek backspace",
                "thoda peeche",
                "peeche jao",
                "peeche hatao",
                "last character hatao",
            ]
        ):
            return self.desktop.press_backspace()

        # Enter / new line: "enter karo", "neeche aa jao", "next line", etc.
        if any(
            phrase in text_lower
            for phrase in [
                "enter karo",
                "enter press",
                "neeche aa jao",
                "next line",
                "new line",
                "nayi line",
                "line break",
            ]
        ):
            return self.desktop.press_enter()

        # ---------------------- Notepad / editor helpers ----------------------

        # Typing into the active window (primarily Notepad / Word / etc.).
        # Examples:
        # - "type hello world"
        # - "notepad pe likho this is a test"
        if "type " in text_lower or "likho " in text_lower:
            trigger_index = max(text_lower.rfind("type "), text_lower.rfind("likho "))
            if trigger_index != -1:
                # Use the original text slice so we preserve casing/punctuation.
                raw_suffix = text[trigger_index:]
                cleaned_suffix = (
                    raw_suffix.replace("type ", "", 1)
                    .replace("likho ", "", 1)
                    .replace("please", "")
                    .strip()
                )
                if cleaned_suffix:
                    return self._type_in_active_editor(cleaned_suffix)

        # Create a new document/tab in the active editor, e.g. Notepad / Word / Excel / PowerPoint.
        # Examples:
        # - "open new tab"
        # - "new file"
        if any(
            phrase in text_lower
            for phrase in ["open new tab", "new tab", "new file", "naya file", "nayi file"]
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
                "isko save karo",
                "ye save karo",
            ]
        ):
            return self._save_in_active_editor()

        # Save the currently open Save dialog directly on Desktop, keeping
        # whatever file name is currently present.
        if any(
            phrase in text_lower
            for phrase in ["save on desktop", "desktop pe save karo", "save to desktop"]
        ):
            return self.desktop.save_current_dialog_to_desktop()

        # Save with explicit name and location, e.g.
        # "save file with name report on desktop"
        if "save file with name" in text_lower:
            named_save_result = self._save_with_name_to_location(text)
            if named_save_result is not None:
                return named_save_result

        # System power commands (these should normally be gated by confirmation in UI)
        if any(
            phrase in text_lower
            for phrase in ["shutdown", "shut down", "band kar do", "system band"]
        ):
            return "SYSTEM_SHUTDOWN_REQUEST"

        if any(
            phrase in text_lower
            for phrase in ["restart", "reboot", "dobara start", "restart karo"]
        ):
            return "SYSTEM_RESTART_REQUEST"

        if any(
            phrase in text_lower
            for phrase in ["sleep", "sleep mode", "sula do", "so jao"]
        ):
            return "SYSTEM_SLEEP_REQUEST"

        # ---------------------- Mouse & scroll controls ----------------------

        # Scroll down / up in the active window
        if any(
            phrase in text_lower
            for phrase in [
                "scroll down",
                "neeche scroll",
                "page down",
                "neeche jao",
                "scroll neeche",
            ]
        ):
            return self.desktop.scroll_down()

        if any(
            phrase in text_lower
            for phrase in [
                "scroll up",
                "upar scroll",
                "page up",
                "upar jao",
                "scroll upar",
            ]
        ):
            return self.desktop.scroll_up()

        # Mouse click – best-effort implementation for "click that"-style commands.
        if any(
            phrase in text_lower
            for phrase in [
                "click that",
                "isko click karo",
                "click karo",
                "left click",
            ]
        ):
            return self.desktop.left_click()

        if any(
            phrase in text_lower
            for phrase in [
                "right click",
                "right-click",
                "right click karo",
            ]
        ):
            return self.desktop.right_click()

        # ---------------------- Browser tab control --------------------------

        if any(
            phrase in text_lower
            for phrase in ["new tab", "open new tab", "naya tab", "nayi tab"]
        ):
            return self.desktop.new_tab()

        if any(
            phrase in text_lower
            for phrase in ["next tab", "aagay wala tab", "agli tab"]
        ):
            return self.desktop.next_tab()

        if any(
            phrase in text_lower
            for phrase in ["previous tab", "pichli tab", "peeche wala tab"]
        ):
            return self.desktop.previous_tab()

        if any(
            phrase in text_lower
            for phrase in ["close tab", "ye tab band karo", "is tab ko band karo"]
        ):
            return self.desktop.close_tab()

        # ---------------------- File & folder helpers ------------------------

        # Create folder commands, e.g. "create folder Projects on desktop"
        if "create folder" in text_lower:
            after = text_lower.split("create folder", 1)[-1].strip()
            location_hint = ""

            if "on desktop" in after or "desktop pe" in after:
                after = after.replace("on desktop", "").replace("desktop pe", "").strip()
                location_hint = "desktop"
            elif "in documents" in after:
                after = after.replace("in documents", "").strip()
                location_hint = "documents"

            name = after.strip().strip('"').strip("'")
            if not name:
                return "Boss, folder ka naam clear nahi tha."

            base_dir = os.path.expanduser("~")
            if location_hint == "desktop":
                base_dir = os.path.join(base_dir, "Desktop")
            elif location_hint == "documents":
                base_dir = os.path.join(base_dir, "Documents")

            full_path = os.path.join(base_dir, name)
            return self.desktop.create_folder(full_path)

        # Open folder commands, e.g. "open folder Downloads", "folder Projects open karo"
        if "open folder" in text_lower or "folder " in text_lower:
            folder_part = text_lower
            if "open folder" in folder_part:
                folder_part = folder_part.split("open folder", 1)[-1]
            elif "folder" in folder_part:
                folder_part = folder_part.split("folder", 1)[-1]

            for filler in ["open", "karo", "kholo", "please"]:
                folder_part = folder_part.replace(filler, "")
            folder_name = folder_part.strip().strip('"').strip("'")

            if folder_name:
                base_dir = os.path.expanduser("~")
                if folder_name in ["desktop", "desktop pe"]:
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

        # Check for Google search
        if "search google for" in text_lower or "google search" in text_lower:
            query = text_lower.replace("search google for", "").replace(
                "google search", ""
            ).strip()
            if query:
                return self.search_google(query)

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