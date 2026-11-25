"""Servidor de la página en vivo.  Uso:  python app.py  ->  http://localhost:5000"""
import threading
from flask import Flask, Response, render_template, jsonify
from events import bus
import runner

app = Flask(__name__)
state = {"running": False}

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/stream")
def stream():
    return Response(bus.stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.post("/run")
def run():
    if state["running"]:
        return jsonify(ok=False, error="Ya hay una ejecución en curso"), 409
    def job():
        state["running"] = True
        try:
            runner.run_flow()
        finally:
            state["running"] = False
    threading.Thread(target=job, daemon=True).start()
    return jsonify(ok=True)

if __name__ == "__main__":
    app.run(port=5000, threaded=True)
