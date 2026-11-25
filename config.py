"""Configuración del demo. Ajusta URLs, selectores y credenciales."""
import os

BASE_URL = "https://preprod.netactica.com/NetAdmin/Admin.aspx"

# Credenciales: mejor por variables de entorno, no las dejes en el código
USERNAME = os.getenv("NETA_USER", "admin")
PASSWORD = os.getenv("NETA_PASS", "")
SUCURSAL = os.getenv("NETA_SUCURSAL", "")   # nombre de la sucursal / punto de venta

# Selectores (TODO: ajustarlos con el inspector de Chrome).
# Formato: (estrategia, valor)  estrategia: "css" | "xpath" | "id"
SEL = {
    "login_user":      ("id", "txtUser"),
    "login_pass":      ("id", "txtPassword"),
    "login_submit":    ("id", "btnLogin"),
    "crear_reserva":   ("xpath", "//*[contains(text(),'Crear Reserva')]"),
    "sucursal_select": ("id", "ddlSucursal"),
    "tab_hoteles":     ("xpath", "//*[contains(text(),'Hoteles')]"),
    "destino":         ("id", "txtDestino"),
    "buscar":          ("id", "btnBuscar"),
    "resultado_hotel": ("css", ".hotel-result"),        # lista de resultados
    "primer_reservar": ("css", ".hotel-result .btn-reservar"),
    "modulo_pago":     ("xpath", "//*[contains(text(),'Pago')]"),
}

DESTINO = "Bogotá"
HEADLESS = False
