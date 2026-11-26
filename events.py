"""Bus de eventos en memoria: el runner publica, la página en vivo consume (SSE)."""
import threading, time, json

class EventBus:
    def __init__(self):
        self.events = []
        self.cond = threading.Condition()

    def emit(self, type_, **data):
        with self.cond:
            self.events.append({"type": type_, "ts": time.time(), **data})
            self.cond.notify_all()

    def stream(self):
        i = 0
        while True:
            with self.cond:
                if i >= len(self.events):
                    self.cond.wait(timeout=15)
                batch, i = self.events[i:], len(self.events)
            if not batch:
                yield ": keepalive\n\n"
            for ev in batch:
                yield f"data: {json.dumps(ev, default=str)}\n\n"

bus = EventBus()