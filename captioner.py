import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["TQDM_DISABLE"] = "1"

import model
import sys
import caption.speech as speech

if __name__ == "__main__":
    try:
        args = model.getName(sys.argv, 'base', True)
        if args:
            args['realtime'] = False if '-nrt' in args else True
            args['use_microphone'] = True
            caption = speech.Speech(args)
            caption.start()
    except KeyboardInterrupt:
        print("\nExiting due to keyboard interrupt.")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting captioner: {e}")
        sys.exit(1)
