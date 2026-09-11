"""Display Environment and Library Versions."""
import sys
import platform

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

print("=" * 70)
print("  HARDWARE, SYSTEM & DEPENDENCY SPECIFICATIONS")
print("=" * 70)
print(f"Operating System   : {platform.system()} {platform.release()} (Build {platform.version()})")
print(f"Processor / CPU    : {platform.processor()}")
print(f"Machine Type       : {platform.machine()}")
print(f"Python Runtime     : {sys.version.split()[0]} ({sys.executable})")
print("-" * 70)
print("INSTALLED AI / MULTIMODAL LIBRARIES:")

libs = [
    ("PyAV (Media Demux)", "av"),
    ("faster-whisper (ASR)", "faster_whisper"),
    ("PyMuPDF (PDF Parser)", "fitz"),
    ("ChromaDB (Vector DB)", "chromadb"),
    ("Sentence-Transformers", "sentence_transformers"),
    ("PySceneDetect (Visual)", "scenedetect"),
    ("OpenCV (Computer Vision)", "cv2"),
]

for label, mod_name in libs:
    try:
        mod = __import__(mod_name)
        ver = getattr(mod, "__version__", "Installed")
        print(f"  - {label:<25} : v{ver}")
    except ImportError:
        print(f"  - {label:<25} : Not Installed")

print("=" * 70)
