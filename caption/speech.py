import sys
from RealtimeSTT import AudioToTextRecorder
from pynput import keyboard
import threading
import os
import signal
import caption.web as web
import caption.gui as gui
import caption.input as input
import caption.log as log
import logging
import atexit

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
        # Register cleanup handler
        atexit.register(self.cleanup)

    def cleanup(self):
        """Clean up resources on exit"""
        self.stop = True
        if self.recorder:
            try:
                self.recorder.stop()
            except:
                pass

    def process_text(self, text):
        print(text, end=" ", flush=True)
        self.transcribed_text.append(text)
        if self.ui:
            try:
                self.ui.addNewLine(text)
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
            with AudioToTextRecorder(
                spinner=True,
                model=self.args['model_name'],
                language=self.args['lang'],
                compute_type="float32",
                #enable_realtime_transcription=True,
                realtime_model_type=self.args['realtime_model'],
                #level=logging.DEBUG,
                debug_mode=True,
                webrtc_sensitivity=0, #if self.args['lang'] is None or 
                min_length_of_recording=self.get_min_length_of_recording(), #0.2 if 'en' in self.args['lang'] else 3 if 'base' in self.args['model_name'] or 'tiny' in self.args['model_name'] else 10,
                silero_sensitivity=0.1,
                min_gap_between_recordings=0.4,
                post_speech_silence_duration = 0.16 / self.recording_scale
            ) as recorder:
                self.recorder = recorder
                print("> ", end="", flush=True)
                while not self.stop:
                    recorder.text(self.process_text)
        except KeyboardInterrupt:
            self.stop = True
        except Exception as e:
            print(f"Error in transcription: {e}")
        finally:
            # Use os._exit only if normal exit fails
            try:
                if self.stop:
                    sys.exit(0)
                else:
                    os._exit(0)
            except:
                os._exit(0)

    def start(self):
        control = input.Input(self.args)
        logger = log.Log(self.args)
        
        transcription_thread = threading.Thread(target=self.main_program)
        transcription_thread.daemon = True  # Mark as daemon so it doesn't prevent program exit
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
