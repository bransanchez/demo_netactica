"""Captura el tráfico de red de Chrome (como la pestaña Network de DevTools)
usando los logs de rendimiento de Selenium (CDP)."""
import json, threading, time
from events import bus

MAX_BODY = 20000

class NetworkCollector(threading.Thread):
    def __init__(self, driver):
        super().__init__(daemon=True)
        self.driver = driver
        self.reqs = {}
        self.stop_flag = threading.Event()

    def run(self):
        while not self.stop_flag.is_set():
            try:
                for entry in self.driver.get_log("performance"):
                    self._handle(json.loads(entry["message"])["message"])
            except Exception:
                pass
            time.sleep(0.25)

    def stop(self):
        self.stop_flag.set()

    def _handle(self, msg):
        m, p = msg.get("method"), msg.get("params", {})
        rid = p.get("requestId")
        if m == "Network.requestWillBeSent":
            r = p["request"]
            self.reqs[rid] = {
                "id": rid, "url": r["url"], "method": r["method"],
                "type": p.get("type", ""), "req_headers": r.get("headers", {}),
                "post_data": r.get("postData"), "t0": p["timestamp"],
                "status": None, "state": "pending",
            }
            bus.emit("net", **self.reqs[rid])
        elif m == "Network.responseReceived" and rid in self.reqs:
            r = p["response"]
            self.reqs[rid].update(status=r["status"], mime=r.get("mimeType"),
                                  res_headers=r.get("headers", {}))
        elif m == "Network.loadingFinished" and rid in self.reqs:
            q = self.reqs[rid]
            q["state"] = "done"
            q["time_ms"] = round((p["timestamp"] - q["t0"]) * 1000)
            q["size"] = p.get("encodedDataLength")
            if q["type"] in ("XHR", "Fetch", "Document"):
                try:
                    b = self.driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": rid})
                    q["body"] = b.get("body", "")[:MAX_BODY]
                except Exception:
                    pass
            bus.emit("net", **q)
        elif m == "Network.loadingFailed" and rid in self.reqs:
            self.reqs[rid].update(state="failed", error=p.get("errorText"))
            bus.emit("net", **self.reqs[rid])
