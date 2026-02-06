"""
Voice Recognition Module
Handles continuous speech-to-text conversion using the speech_recognition library.
"""

import speech_recognition as sr
import threading
import queue


class VoiceRecognizer:
    """
    A class to handle continuous voice recognition from microphone input.
    """
    
    def __init__(self):
        """Initialize the voice recognizer with default settings."""
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.audio_queue = queue.Queue()
        self.is_listening = False
        self.recognition_thread = None
        
        # Adjust for ambient noise
        print("Adjusting for ambient noise... Please wait.")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Ambient noise adjustment complete.")
    
    def recognize_audio(self, audio_data):
        """
        Convert audio data to text using Google's speech recognition.

        This method is bilingual-friendly:
        - First, it tries to recognize English (default)
        - If that fails with an UnknownValueError, it tries Urdu (ur-PK)

        Args:
            audio_data: Audio data from the microphone

        Returns:
            str: Recognized text (lowercased) or None if recognition fails
        """
        # 1) Try English (default behaviour – keeps existing commands working)
        try:
            text = self.recognizer.recognize_google(audio_data)
            return text.lower()
        except sr.UnknownValueError:
            # 2) Try Urdu as a fallback
            try:
                text = self.recognizer.recognize_google(audio_data, language="ur-PK")
                return text.lower()
            except sr.UnknownValueError:
                # Speech was unintelligible in both languages
                return None
            except sr.RequestError as e:
                print(f"Could not request results from Urdu speech recognition: {e}")
                return None
        except sr.RequestError as e:
            # API was unreachable or unresponsive
            print(f"Could not request results from speech recognition service: {e}")
            return None
    
    def listen_continuously(self, callback, status_callback=None):
        """
        Continuously listen to microphone input and process speech.
        
        Args:
            callback: Function to call when speech is recognized (receives text as parameter)
            status_callback: Optional function to call with status updates
        """
        self.is_listening = True
        
        def audio_capture_thread():
            """Thread function to continuously capture audio."""
            with self.microphone as source:
                while self.is_listening:
                    try:
                        if status_callback:
                            status_callback("listening")

                        # Let the recognizer listen until it detects a phrase
                        # based on ambient noise and internal VAD, without a
                        # fixed phrase_time_limit so the user can speak
                        # naturally and pause briefly.
                        audio = self.recognizer.listen(source)

                        if status_callback:
                            status_callback("processing")

                        # Recognize speech
                        text = self.recognize_audio(audio)

                        if text:
                            callback(text)

                    except sr.WaitTimeoutError:
                        # Timeout is normal, continue listening
                        continue
                    except Exception as e:
                        if status_callback:
                            status_callback(f"error: {str(e)}")
                        print(f"Error in audio capture: {e}")
                        continue
        
        # Start the recognition thread
        self.recognition_thread = threading.Thread(target=audio_capture_thread, daemon=True)
        self.recognition_thread.start()
    
    def stop_listening(self):
        """Stop the continuous listening process."""
        self.is_listening = False
        if self.recognition_thread:
            self.recognition_thread.join(timeout=2)

