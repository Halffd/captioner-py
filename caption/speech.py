import os
import sys
cpu_threads = os.cpu_count()
os.environ["OMP_NUM_THREADS"] = str(cpu_threads)
os.environ["MKL_NUM_THREADS"] = str(cpu_threads)
os.environ["NUMEXPR_NUM_THREADS"] = str(cpu_threads)
os.environ["OMP_WAIT_POLICY"] = "ACTIVE"  # Better performance
from RealtimeSTT import AudioToTextRecorder
from pynput import keyboard
import threading
import signal
import caption.web as web
import caption.gui as gui
import caption.input as input
import caption.log as log
import logging
import atexit

# Suppress ALSA warnings
os.environ['ALSA_CARD'] = 'default'

DEBUG = False
if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
class Speech:
    def __init__(self, args):
        self.transcribed_text = []
        self.quit_program = False
        self.ui = None
        self.args = args
        self.stop = False
        self.recorder = None
        self.recording_scale = 1.25
        self.recording_enabled = True
        # Register cleanup handler
        atexit.register(self.cleanup)

    def toggle_recording(self):
        self.recording_enabled = not self.recording_enabled
        if self.ui:
            self.ui.updateRecordingStatus(self.recording_enabled)

    def cleanup(self):
        """Clean up resources on exit"""
        self.stop = True
        if self.recorder:
            try:
                # Stop the recorder with a timeout to prevent hanging
                self.recorder.stop()
            except Exception as e:
                print(f"Error stopping recorder: {e}")
                pass

    def process_text(self, text):
        if not self.recording_enabled:
            return
        print(text, end=" ", flush=True)
        self.transcribed_text.append(text)
        if self.ui:
            try:
                self.ui.newLineSignal.emit(text)
            except Exception as e:
                print(f"Error adding new line to UI: {e}")

    def get_min_length_of_recording(self):
        conditionsHigh = {
            ('en', 'tiny.en'): 1.5,
            ('en', 'tiny'): 1.75,
            ('en', 'base.en'): 2.2,
            ('en', 'base'): 2.25,
            ('en', 'small.en'): 3.8,
            ('en', 'small'): 3.85,
            ('en', 'medium.en'): 7.8,
            ('en', 'medium'): 7.85,
            ('en', 'large'): 12.5,
            ('en', 'large-v2'): 19,
            ('en', 'large-v3'): 48,
            ('', 'tiny'): 2,
            ('', 'base'): 3,
            ('', 'small'): 5,
            ('', 'medium'): 10,
            ('', 'large'): 20,
            ('', 'large-v2'): 30,
            ('', 'large-v3'): 50,
        }
        conditions = {
            ('en', 'tiny.en'): 1.5,
            ('en', 'tiny'): 1.75,
            ('en', 'base.en'): 2,
            ('en', 'base'): 2.25,
            ('en', 'small.en'): 2.8,
            ('en', 'small'): 2.85,
            ('en', 'medium.en'): 3.8,
            ('en', 'medium'): 3.85,
            ('en', 'large'): 4.5,
            ('en', 'large-v2'): 5,
            ('en', 'large-v3'): 8,
            ('', 'tiny'): 2,
            ('', 'base'): 3,
            ('', 'small'): 4,
            ('', 'medium'): 5,
            ('', 'large'): 7,
            ('', 'large-v2'): 9,
            ('', 'large-v3'): 12,
        }

        lang = 'en' if not self.args['lang'] is None and 'en' in self.args['lang'] else ''

        return conditions.get((lang, self.args['model_name']), 1) * self.recording_scale
    
    def main_program(self):
        try:
            import time
            print("Initializing audio recorder...")
            # Initialize the recorder with current settings
            recorder = AudioToTextRecorder(
                spinner=True,
                model=self.args['model_name'],
                device='cpu',
                language=self.args['lang'],
                enable_realtime_transcription=self.args['realtime'],
#                use_microphone=self.args['use_microphone'],
#                model_path=None,
                realtime_model_type=self.args['realtime_model'],
                #level=logging.DEBUG,
                debug_mode=True,
                webrtc_sensitivity=0,
                min_length_of_recording=self.get_min_length_of_recording() / 3,
                silero_sensitivity=0.1,
                min_gap_between_recordings=0.4,
                post_speech_silence_duration = 0.16 / self.recording_scale
            )

            # Store the recorder in the instance
            self.recorder = recorder

            print("Audio recorder initialized. Starting transcription. Say something...")

            print("> ", end="", flush=True)
            while not self.stop:
                try:
                    # Process text from the recorder
                    # The RealtimeSTT library's text() method blocks until a full sentence/phrase is detected
                    # Check stop flag before each blocking call
                    if self.stop:
                        break
                    recorder.text(self.process_text)
                except Exception as e:
                    if self.stop:
                        break
                    print(f"Error in recording: {e}")
                    # Short sleep to allow other threads to process stop commands
                    time.sleep(0.01)

        except KeyboardInterrupt:
            print("Keyboard interrupt received")
            self.stop = True
        except Exception as e:
            print(f"Error in transcription: {e}")
            print("This may be due to missing audio devices. Ensure audio is properly configured.")
        finally:
            # Clean up the recorder
            if self.recorder:
                try:
                    self.recorder.stop()
                    print("Audio recorder stopped")
                except:
                    pass
                self.recorder = None

    def start(self):
        control = input.Input(self.args)
        logger = log.Log(self.args)
        
        transcription_thread = threading.Thread(target=self.main_program)
        transcription_thread.start()

        try:
            if self.args.get('gui', False):
                self.ui = gui.initialize()
                self.ui.language = self.args['lang']
                self.ui.speech = self
                self.ui.log = logger
                control.gui = self.ui
                self.ui.run()
            elif self.args.get('web', False):
                web.Web(self.args).start_server()
            
            # Wait for transcription to complete
            transcription_thread.join()
        except KeyboardInterrupt:
            print("\nReceived keyboard interrupt. Exiting...")
        except Exception as e:
            print(f"Error in main program: {e}")
        finally:
            self.stop = True
            if logger.file:
                logger.close_log_file()
