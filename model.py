import sys
import re
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["TQDM_DISABLE"] = "1"

first = True

model_names = [
    "tiny", "base", "small", "medium",
    "large", "large-v2", "large-v3",
    "tiny.en", "base.en", "small.en", "medium.en",
    "jlondonobo/whisper-medium-pt",
    "clu-ling/whisper-large-v2-japanese-5k-steps",
    "distil-whisper/distil-medium.en",
    "distil-whisper/distil-small.en",
    "distil-whisper/distil-base",
    "distil-whisper/distil-small",
    "distil-whisper/distil-medium",
    "distil-whisper/distil-large",
    "distil-whisper/distil-large-v2",
    "distil-whisper/distil-large-v3",
    "Systran/faster-distil-medium",
    "Systran/faster-distil-large",
    "Systran/faster-distil-large-v2",
    "Systran/faster-distil-large-v3",
    "japanese-asr/distil-whisper-large-v3-ja-reazonspeech-large",
]

# ---------- helpers ----------

def is_numeric(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def looks_like_lang(s):
    # ja, en, pt, zh, zh-CN, en-US
    return bool(re.fullmatch(r"[a-z]{2,3}(-[A-Z]{2})?", s))

def list_audio_devices():
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        print("\n=== Available Audio Input Devices ===")
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if dev['maxInputChannels'] > 0:
                print(f"  [{i}] {dev['name']} (hw:{dev['hostApi']},{dev['index']}) - {dev['maxInputChannels']} ch, {int(dev['defaultSampleRate'])} Hz")
        print("\n=== Available Audio Output Devices (for monitoring) ===")
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if dev['maxOutputChannels'] > 0:
                print(f"  [{i}] {dev['name']} (hw:{dev['hostApi']},{dev['index']}) - {dev['maxOutputChannels']} ch, {int(dev['defaultSampleRate'])} Hz")
        print("\n=== Hints ===")
        print("  --input <name or index>   Select input device (microphone)")
        print("  --output <name or index>  Select output device for monitor capture (PulseAudio:monitor, etc.)")
        print("  Use index number or a substring of the device name")
        p.terminate()
    except Exception as e:
        print(f"Error listing devices: {e}")
        print("Install pyaudio: pip install pyaudio")

def resolve_model(token, default):
    if is_numeric(token):
        idx = int(token)
        if 0 <= idx < len(model_names):
            return model_names[idx]
        return default
    return token

# ---------- main parser ----------

def getName(argv, default, captioner=False):
    global first
    if not first:
        return

    result = {
        "model_name": default,
        "realtime_model": None,
        "lang": None,
        "gui": False,
        "web": False,
        "debug_mode": False,
        "test_mode": False,
        "realtime": True,
        "path": os.getcwd(),
        "input_device": None,
        "output_device": None,
    }

    args = argv[1:]

    # handle simple flags (no verbosity explosion)
    cleaned = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-g", "--gui"):
            result["gui"] = True
        elif a in ("-w", "--web"):
            result["web"] = True
        elif a == "--debug":
            result["debug_mode"] = True
        elif a == "--test":
            result["test_mode"] = True
        elif a in ("-i", "--input"):
            i += 1
            if i < len(args) and not args[i].startswith("-"):
                result["input_device"] = args[i]
        elif a in ("-o", "--output"):
            i += 1
            if i < len(args) and not args[i].startswith("-"):
                result["output_device"] = args[i]
        elif a in ("--list-devices", "-ld"):
            list_audio_devices()
            sys.exit(0)
        elif a == "-nrt" or a == "--no-realtime":
            result["realtime"] = False
        else:
            cleaned.append(a)
        i += 1

    # positional meaning:
    # [model] [realtime_model] [language]
    pos = 0
    for token in cleaned:
        if looks_like_lang(token) and result["lang"] is None:
            result["lang"] = token
        elif pos == 0:
            result["model_name"] = resolve_model(token, default)
            pos += 1
        elif pos == 1:
            result["realtime_model"] = resolve_model(token, result["model_name"])
            pos += 1
        else:
            pass  # ignore extra junk

    # defaults
    if result["realtime_model"] is None:
        result["realtime_model"] = result["model_name"]

    # safety: multilingual vs .en
    if result["lang"] and result["lang"] != "en":
        if ".en" in result["model_name"]:
            raise ValueError(
                f"Model '{result['model_name']}' is English-only but lang={result['lang']}"
            )

    if result["model_name"] not in model_names:
        print(f"Warning: {result['model_name']} is not a recognized model name")

    print(result)
    first = False
    return result
