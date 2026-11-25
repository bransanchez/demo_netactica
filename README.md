# Demo Netactica – Selenium + página en vivo

## Instalar
    pip install -r requirements.txt

## Configurar
Edita `config.py` (URL, selectores, destino). Credenciales por variables de entorno:

    export NETA_USER=usuario
    export NETA_PASS=clave
    export NETA_SUCURSAL="Nombre sucursal"     # Windows: set NETA_USER=...

## Ejecutar
    python app.py
Abre http://localhost:5000 y pulsa **Ejecutar**.

## Cómo funciona
- `runner.py`: flujo Selenium (login → reservas → sucursal → búsqueda → selección → pago).
- `network.py`: lee los logs de rendimiento de Chrome (CDP) y emite cada petición.
- `events.py` + `app.py`: bus de eventos y servidor Flask con SSE.
- `templates/index.html`: página en vivo (pasos, tabla Network con detalle, capturas).
