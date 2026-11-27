"""Servidor de la página en vivo. Uso: python app.py -> http://localhost:5000"""
import threading
from flask import Flask, Response, render_template, jsonify, send_from_directory
from events import bus
import runner
from pathlib import Path

app = Flask(__name__, static_folder="static")
state = {"running": False}

# Directorio de grabaciones
RECORDINGS_DIR = Path(__file__).parent / "static" / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


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


@app.post("/run_hotel")
def run_hotel():
    if state["running"]:
        return jsonify(ok=False, error="Ya hay una ejecución en curso"), 409

    def job():
        state["running"] = True
        try:
            runner.run_hotel()
        finally:
            state["running"] = False
    threading.Thread(target=job, daemon=True).start()
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(port=5000, threaded=True)
