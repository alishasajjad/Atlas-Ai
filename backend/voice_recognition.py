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
        self.microphone = None  # Will be initialized when needed
        self.audio_queue = queue.Queue()
        self.is_listening = False
        self.recognition_thread = None
        self._microphone_context = None  # Track context manager
    
    def recognize_audio(self, audio_data):
        """
        Convert audio data to text using Google's speech recognition.
        English-only recognition.

        Args:
            audio_data: Audio data from the microphone

        Returns:
            str: Recognized text (lowercased) or None if recognition fails
        """
        try:
            text = self.recognizer.recognize_google(audio_data, language="en-US")
            return text.lower()
        except sr.UnknownValueError:
            # Speech was unintelligible
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
        if self.is_listening:
            return  # Already listening
        
        self.is_listening = True
        
        # Initialize microphone if not already done
        if self.microphone is None:
            try:
                self.microphone = sr.Microphone()
                # Adjust for ambient noise
                print("Adjusting for ambient noise... Please wait.")
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("Ambient noise adjustment complete.")
            except Exception as e:
                print(f"Error initializing microphone: {e}")
                self.is_listening = False
                return
        
        def audio_capture_thread():
            """Thread function to continuously capture audio."""
            try:
                with self.microphone as source:
                    self._microphone_context = source
                    while self.is_listening:
                        try:
                            if status_callback:
                                status_callback("listening")

                            # Let the recognizer listen until it detects a phrase
                            audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)

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
            except Exception as e:
                print(f"Error in microphone context: {e}")
            finally:
                self._microphone_context = None
        
        # Start the recognition thread
        self.recognition_thread = threading.Thread(target=audio_capture_thread, daemon=True)
        self.recognition_thread.start()
    
    def stop_listening(self):
        """Stop the continuous listening process."""
        self.is_listening = False
        # Give thread time to exit gracefully
        if self.recognition_thread:
            self.recognition_thread.join(timeout=2)
        # Clear microphone context reference
        self._microphone_context = None

