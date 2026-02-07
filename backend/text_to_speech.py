"""
Text-to-Speech Module
Handles audio responses using pyttsx3 library.
"""

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

import threading


class TextToSpeech:
    """
    A class to handle text-to-speech conversion using pyttsx3.
    """

    def __init__(self):
        """Initialize the TTS engine with default settings."""
        self.engine = None
        self.is_speaking = False
        # When muted, Nova will keep generating responses but will not
        # play them through the speakers until unmuted via voice command.
        self.muted = False

        # Try to initialize pyttsx3 engine (may fail on headless Linux)
        if pyttsx3 is not None:
            try:
                self.engine = pyttsx3.init()
                self.setup_voice()
            except Exception as e:
                print(f"TTS engine initialization failed (expected on cloud): {e}")
                self.engine = None

    def setup_voice(self):
        """Configure voice rate, volume, and voice selection."""
        if self.engine is None:
            return

        try:
            # Get available voices
            voices = self.engine.getProperty("voices")

            # Clear, natural speech rate for English
            self.engine.setProperty("rate", 140)  # Speed of speech
            self.engine.setProperty("volume", 0.95)  # Volume level (0.0 to 1.0)

            # Try to choose a clear English voice.
            # This heavily depends on which voices are installed on Windows, so we use
            # best-effort heuristics and always fall back gracefully.
            selected_id = None
            if voices:
                # Prefer English voices
                english_keywords = ["english", "en-", "us", "uk", "zira", "david"]
                for voice in voices:
                    name_lower = voice.name.lower()
                    id_lower = str(getattr(voice, "id", "")).lower()
                    if any(k in name_lower for k in english_keywords) or any(
                        k in id_lower for k in english_keywords
                    ):
                        selected_id = voice.id
                        break

                # Otherwise, prefer a neutral/female voice
                if selected_id is None:
                    for voice in voices:
                        name_lower = voice.name.lower()
                        if "female" in name_lower or "zira" in name_lower:
                            selected_id = voice.id
                            break

            if selected_id is not None:
                self.engine.setProperty("voice", selected_id)
        except Exception as e:
            print(f"TTS voice setup failed (non-fatal): {e}")

    def speak(self, text):
        """
        Convert text to speech and play it.

        Args:
            text: The text to be spoken
        """
        if not text or self.muted or self.engine is None:
            return

        def speak_thread():
            """Thread function to speak without blocking."""
            try:
                self.is_speaking = True
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"Error in text-to-speech: {e}")
            finally:
                self.is_speaking = False

        # Speak in a separate thread to avoid blocking
        thread = threading.Thread(target=speak_thread, daemon=True)
        thread.start()

    def stop(self):
        """Stop any ongoing speech."""
        try:
            if self.engine is not None:
                self.engine.stop()
            self.is_speaking = False
        except Exception as e:
            print(f"Error stopping speech: {e}")

    def mute(self):
        """Mute future speech until explicitly unmuted."""
        self.muted = True
        # Also stop anything that is currently being spoken.
        self.stop()

    def set_rate(self, rate: int):
        """Set the speech rate (speed). Default is around 200, we use 140."""
        if self.engine is None:
            return
        try:
            self.engine.setProperty("rate", rate)
        except Exception as e:
            print(f"Error setting rate: {e}")

    def set_volume(self, volume: float):
        """Set the volume level (0.0 to 1.0)."""
        if self.engine is None:
            return
        try:
            self.engine.setProperty("volume", volume)
        except Exception as e:
            print(f"Error setting volume: {e}")

    def unmute(self):
        """Allow Nova to speak responses again."""
        self.muted = False
