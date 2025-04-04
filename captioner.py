import model
import sys
import os
import caption.speech as speech

if __name__ == "__main__":
    try:
        args = model.getName(sys.argv, 'base', True)
        if args:
            caption = speech.Speech(args)
            caption.start()
    except KeyboardInterrupt:
        print("\nExiting due to keyboard interrupt.")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting captioner: {e}")
        sys.exit(1)