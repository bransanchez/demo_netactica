"""Bus de eventos en memoria: el runner publica, la página en vivo consume (SSE)."""
import json, threading, time


class EventBus:
    def __init__(self):
        self.events = []
        self.cond = threading.Condition()

    def emit(self, type_, **data):
        ev = dict(data)
        # Las peticiones de red traen su propia clave "type" (XHR, Script, Document...).
        # No debe pisar el tipo del evento: se guarda aparte como "rtype".
        if "type" in ev:
            ev["rtype"] = ev.pop("type")
        ev["type"] = type_
        ev["ts"] = time.time()
        with self.cond:
            self.events.append(ev)
            self.cond.notify_all()

    def stream(self):
        yield ": connected\n\n"
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
