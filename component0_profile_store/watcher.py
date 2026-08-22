import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from store import sync_resumes
from pathlib import Path

import requests

class ResumeChangeHandler(FileSystemEventHandler):
    """Reacts to file-system events inside resumes/ by re-running sync_resumes()."""

    def on_created(self, event):
        self._maybe_sync(event)

    def on_modified(self, event):
        self._maybe_sync(event)

    def _maybe_sync(self, event):
        if event.is_directory:
            return 
        if not event.src_path.lower().endswith(".pdf"):
            return
        print(f"Detected change: {event.src_path}")
        for attempt in range(5):
            try:
                sync_resumes()
                return
            except PermissionError:
                time.sleep(0.5)
            except requests.exceptions.ConnectionError:
                print("Ollama isn't reachable at localhost:11434 - is it running?")
                return

if __name__ == "__main__":
    resumes_path = Path(__file__).resolve().parent / "resumes"

    event_handler = ResumeChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path=resumes_path, recursive=False)

    observer.start()
    print(f"Watching {resumes_path}/ for resume changes... (Ctrl + C to stop)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()