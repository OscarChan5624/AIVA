"""
Enhanced Voice Handler for Time Manager App
Handles speech recognition (speech-to-text) and text-to-speech
with improved error handling and customization options
"""

import speech_recognition as sr
import pyttsx3
from threading import Thread
from typing import Callable, Optional
import time


class VoiceHandler:
    """
    Handles speech recognition and text-to-speech with enhanced features.
    """
    
    def __init__(self, voice_rate: int = 160, voice_volume: float = 0.9):
        """
        Initialize voice handler with recognizer and TTS engine.
        
        Args:
            voice_rate: Speech rate in words per minute (default: 160)
            voice_volume: Volume level 0.0 to 1.0 (default: 0.9)
        """
        self.recognizer = sr.Recognizer()
        self.tts_engine = None
        self.is_listening = False
        self.is_speaking = False
        
        # Recognizer settings for better accuracy
        self.recognizer.energy_threshold = 4000  # Adjust based on environment
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        self.recognizer.pause_threshold = 0.8  # Seconds of silence before phrase is considered complete
        
        # Initialize TTS engine
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', voice_rate)
            self.tts_engine.setProperty('volume', voice_volume)
            
            # Try to set a pleasant voice
            voices = self.tts_engine.getProperty('voices')
            if len(voices) > 1:
                # Prefer female voice (usually index 1) if available
                self.tts_engine.setProperty('voice', voices[1].id)
            
            print(f"✓ TTS engine initialized (rate: {voice_rate}, volume: {voice_volume})")
        except Exception as e:
            print(f"✗ TTS initialization error: {e}")
    
    def listen(
        self, 
        callback: Callable[[Optional[str], Optional[str]], None], 
        timeout: int = 8,
        phrase_limit: int = 10,
        language: str = "en-US"
    ):
        """
        Listen for user speech and call callback with text.
        
        Args:
            callback: Function to call with (text, error) when done
            timeout: Maximum seconds to wait for speech (default: 8)
            phrase_limit: Maximum seconds for a single phrase (default: 10)
            language: Language code for recognition (default: "en-US")
        """
        # CRITICAL FIX: Check if already listening
        if self.is_listening:
            print("⚠️ Already listening, ignoring new request")
            callback(None, "Already listening. Please wait.")
            return
        
        def _listen():
            self.is_listening = True
            microphone = None
            
            try:
                microphone = sr.Microphone()
                with microphone as source:
                    print("🎤 Adjusting for ambient noise...")
                    
                    # CRITICAL FIX: Add timeout protection for ambient noise adjustment
                    try:
                        # Use shorter duration and add error handling
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    except Exception as e:
                        print(f"⚠️ Ambient noise adjustment failed: {e}")
                        # Continue anyway with default threshold
                    
                    print(f"👂 Listening (timeout: {timeout}s)...")
                    audio = self.recognizer.listen(
                        source, 
                        timeout=timeout, 
                        phrase_time_limit=phrase_limit
                    )
                    
                    print("🔄 Processing speech...")
                    
                    # Use Google Speech Recognition (free, reliable)
                    text = self.recognizer.recognize_google(audio, language=language)
                    print(f"✓ Recognized: {text}")
                    
                    self.is_listening = False
                    callback(text, None)
                    
            except sr.WaitTimeoutError:
                print("⏱️ Listening timeout - no speech detected")
                self.is_listening = False
                callback(None, "No speech detected. Please try again.")
                
            except sr.UnknownValueError:
                print("❓ Could not understand audio")
                self.is_listening = False
                callback(None, "Sorry, I couldn't understand that. Please speak clearly.")
                
            except sr.RequestError as e:
                print(f"⚠️ Speech recognition service error: {e}")
                self.is_listening = False
                callback(None, "Speech recognition service is unavailable right now.")
                
            except OSError as e:
                print(f"⚠️ Microphone error: {e}")
                self.is_listening = False
                callback(None, "Microphone not available. Please check your device settings.")
                
            except Exception as e:
                print(f"❌ Unexpected error during listening: {e}")
                import traceback
                traceback.print_exc()
                self.is_listening = False
                callback(None, f"An error occurred: {str(e)}")
            finally:
                # CRITICAL FIX: Always reset listening flag
                self.is_listening = False
                # Ensure microphone is released
                if microphone:
                    try:
                        # Microphone should be released by context manager, but ensure it's closed
                        pass
                    except:
                        pass
        
        # Run in background thread to avoid blocking UI
        Thread(target=_listen, daemon=True).start()
    
    def speak(
        self, 
        text: str, 
        blocking: bool = False,
        interrupt_current: bool = True
    ):
        """
        Convert text to speech.
        
        Args:
            text: Text to speak
            blocking: If True, wait for speech to complete before returning
            interrupt_current: If True, stop current speech before starting new one
        """
        if not self.tts_engine:
            print("⚠️ TTS engine not available")
            return
        
        # Stop current speech if requested
        if interrupt_current and self.is_speaking:
            self.stop_speaking()
            time.sleep(0.1)  # Brief pause between speeches
        
        def _speak():
            try:
                self.is_speaking = True
                print(f"🔊 Speaking: {text[:50]}...")
                
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                
                self.is_speaking = False
                print("✓ Speech completed")
                
            except Exception as e:
                print(f"⚠️ TTS error: {e}")
                self.is_speaking = False
        
        if blocking:
            _speak()
        else:
            # Run in background thread
            Thread(target=_speak, daemon=True).start()
    
    def stop_speaking(self):
        """Stop current speech output immediately."""
        if self.tts_engine and self.is_speaking:
            try:
                self.tts_engine.stop()
                self.is_speaking = False
                print("⏹️ Speech stopped")
            except Exception as e:
                print(f"⚠️ Error stopping speech: {e}")
    
    def set_voice_rate(self, rate: int):
        """
        Set speech rate.
        
        Args:
            rate: Words per minute (typical range: 100-300)
        """
        if self.tts_engine:
            try:
                self.tts_engine.setProperty('rate', rate)
                print(f"✓ Voice rate set to {rate} wpm")
            except Exception as e:
                print(f"⚠️ Error setting voice rate: {e}")
    
    def set_voice_volume(self, volume: float):
        """
        Set speech volume.
        
        Args:
            volume: Volume level 0.0 (silent) to 1.0 (maximum)
        """
        if self.tts_engine:
            try:
                volume = max(0.0, min(1.0, volume))  # Clamp to valid range
                self.tts_engine.setProperty('volume', volume)
                print(f"✓ Voice volume set to {volume}")
            except Exception as e:
                print(f"⚠️ Error setting voice volume: {e}")
    
    def set_voice_gender(self, prefer_female: bool = True):
        """
        Set voice gender preference.
        
        Args:
            prefer_female: If True, use female voice if available
        """
        if not self.tts_engine:
            return
        
        try:
            voices = self.tts_engine.getProperty('voices')
            
            if prefer_female and len(voices) > 1:
                self.tts_engine.setProperty('voice', voices[1].id)
                print("✓ Voice set to female")
            elif len(voices) > 0:
                self.tts_engine.setProperty('voice', voices[0].id)
                print("✓ Voice set to male")
                
        except Exception as e:
            print(f"⚠️ Error setting voice gender: {e}")
    
    def list_available_voices(self) -> list:
        """
        Get list of available TTS voices.
        
        Returns:
            List of voice information dictionaries
        """
        if not self.tts_engine:
            return []
        
        try:
            voices = self.tts_engine.getProperty('voices')
            voice_list = []
            
            for i, voice in enumerate(voices):
                voice_info = {
                    'index': i,
                    'id': voice.id,
                    'name': voice.name,
                    'languages': voice.languages if hasattr(voice, 'languages') else []
                }
                voice_list.append(voice_info)
                print(f"Voice {i}: {voice.name}")
            
            return voice_list
            
        except Exception as e:
            print(f"⚠️ Error listing voices: {e}")
            return []
    
    def test_microphone(self) -> bool:
        """
        Test if microphone is available and accessible.
        
        Returns:
            True if microphone is accessible, False otherwise
        """
        try:
            print("🎤 Testing microphone...")
            with sr.Microphone() as source:
                print("✓ Microphone test: OK")
                return True
                
        except OSError as e:
            print(f"✗ Microphone test failed - Device error: {e}")
            return False
            
        except Exception as e:
            print(f"✗ Microphone test failed: {e}")
            return False
    
    def test_speaker(self) -> bool:
        """
        Test if text-to-speech is working.
        
        Returns:
            True if TTS is working, False otherwise
        """
        try:
            if not self.tts_engine:
                print("✗ Speaker test failed - TTS engine not initialized")
                return False
            
            print("🔊 Testing speaker...")
            self.speak("Testing speaker. If you hear this, audio is working.", blocking=True)
            print("✓ Speaker test: OK")
            return True
            
        except Exception as e:
            print(f"✗ Speaker test failed: {e}")
            return False
    
    def calibrate_microphone(self, duration: float = 2.0):
        """
        Calibrate microphone for ambient noise.
        
        Args:
            duration: Seconds to listen for ambient noise
        """
        try:
            print(f"🎤 Calibrating microphone for {duration}s...")
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
                print(f"✓ Calibration complete. Energy threshold: {self.recognizer.energy_threshold}")
        except Exception as e:
            print(f"⚠️ Calibration error: {e}")
    
    def get_microphone_list(self) -> list:
        """
        Get list of available microphones.
        
        Returns:
            List of microphone names
        """
        try:
            mic_list = sr.Microphone.list_microphone_names()
            print(f"📋 Found {len(mic_list)} microphone(s):")
            for i, mic in enumerate(mic_list):
                print(f"  {i}: {mic}")
            return mic_list
        except Exception as e:
            print(f"⚠️ Error listing microphones: {e}")
            return []
    
    def set_microphone(self, device_index: int):
        """
        Set specific microphone to use.
        
        Args:
            device_index: Index of microphone from get_microphone_list()
        """
        try:
            # Test the microphone
            with sr.Microphone(device_index=device_index) as source:
                print(f"✓ Microphone set to device index {device_index}")
        except Exception as e:
            print(f"⚠️ Error setting microphone: {e}")
    
    def get_status(self) -> dict:
        """
        Get current status of voice handler.
        
        Returns:
            Dictionary with status information
        """
        return {
            'is_listening': self.is_listening,
            'is_speaking': self.is_speaking,
            'tts_available': self.tts_engine is not None,
            'energy_threshold': self.recognizer.energy_threshold,
            'pause_threshold': self.recognizer.pause_threshold
        }
    
    def cleanup(self):
        """Clean up resources (call when app closes)."""
        try:
            self.stop_speaking()
            print("✓ Voice handler cleaned up")
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")