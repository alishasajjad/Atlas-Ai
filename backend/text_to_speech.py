"""
Text-to-Speech Module
Handles audio responses using pyttsx3 library.
"""

import pyttsx3
import threading


class TextToSpeech:
    """
    A class to handle text-to-speech conversion using pyttsx3.
    """
    
    def __init__(self):
        """Initialize the TTS engine with default settings."""
        self.engine = pyttsx3.init()
        self.is_speaking = False
        # When muted, Nova will keep generating responses but will not
        # play them through the speakers until unmuted via voice command.
        self.muted = False

        # Configure voice properties
        self.setup_voice()
    
    def setup_voice(self):
        """Configure voice rate, volume, and voice selection."""
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
    
    def speak(self, text):
        """
        Convert text to speech and play it.
        
        Args:
            text: The text to be spoken
        """
        if not text or self.muted:
            # Either there is nothing to say, or voice output has been
            # muted via a "stop speaking" or "mute" command.
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
            self.engine.stop()
            self.is_speaking = False
        except Exception as e:
            print(f"Error stopping speech: {e}")

    def mute(self):
        """Mute future speech until explicitly unmuted."""
        self.muted = True
        # Also stop anything that is currently being spoken.
        self.stop()

    def unmute(self):
        """Allow Nova to speak responses again."""
        self.muted = False

