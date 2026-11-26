"""Configuración del demo. Ajusta URLs, selectores y credenciales."""
import os

BASE_URL = "https://preprod.netactica.com/NetAdmin/Login.aspx"

# Credenciales: por variables de entorno, nunca escritas en el código
USERNAME = os.getenv("NETA_USER", "")
PASSWORD = os.getenv("NETA_PASS", "")
SERVICE = os.getenv("NETA_SERVICE", "")     # campo "UserService" del login (ej. regresion)
SUCURSAL = os.getenv("NETA_SUCURSAL", "")   # nombre de la sucursal / punto de venta

# Selectores. Formato: (estrategia, valor)  estrategia: "css" | "xpath" | "id"
SEL = {
    # Login (ya reales)
    "login_user":      ("id", "Login_UserName"),
    "login_pass":      ("id", "Login_Password"),
    "login_service":   ("id", "Login_UserService"),
    "login_submit":    ("id", "Login_btnLogin"),

    # TODO: pendientes, se llenan con selectores_MENU.txt, selectores_BUSQUEDA.txt, etc.
    "crear_reserva":   ("xpath", "//*[contains(text(),'Crear Reserva')]"),
    "sucursal_select": ("id", "ddlSucursal"),
    "tab_hoteles":     ("xpath", "//*[contains(text(),'Hoteles')]"),
    "destino":         ("id", "txtDestino"),
    "buscar":          ("id", "btnBuscar"),
    "resultado_hotel": ("css", ".hotel-result"),
    "primer_reservar": ("css", ".hotel-result .btn-reservar"),
    "modulo_pago":     ("xpath", "//*[contains(text(),'Pago')]"),
}

DESTINO = "Bogotá"
HEADLESS = False
