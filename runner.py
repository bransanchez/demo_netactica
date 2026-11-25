"""Flujo Selenium: login -> sucursal -> búsqueda -> selección -> módulo de pago."""
import base64, traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

import config
from events import bus
from network import NetworkCollector

BY = {"css": By.CSS_SELECTOR, "xpath": By.XPATH, "id": By.ID}
STEPS = [
    "Iniciar sesión", "Abrir módulo de reservas", "Seleccionar sucursal",
    "Buscar hoteles", "Seleccionar resultado", "Llegar al módulo de pago",
]

def build_driver():
    opts = webdriver.ChromeOptions()
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    if config.HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1440,900")
    d = webdriver.Chrome(options=opts)          # Selenium Manager baja el driver solo
    d.execute_cdp_cmd("Network.enable", {})
    return d

def loc(key):
    kind, val = config.SEL[key]
    return BY[kind], val

def run_flow():
    bus.emit("reset", steps=STEPS)
    driver, net = None, None
    current = None

    def step(i, fn):
        nonlocal current
        current = i
        bus.emit("step", index=i, name=STEPS[i], status="running")
        fn()
        shot = base64.b64encode(driver.get_screenshot_as_png()).decode()
        bus.emit("step", index=i, name=STEPS[i], status="ok", screenshot=shot)

    try:
        driver = build_driver()
        net = NetworkCollector(driver); net.start()
        wait = WebDriverWait(driver, 30)
        click = lambda k: wait.until(EC.element_to_be_clickable(loc(k))).click()
        type_ = lambda k, t: wait.until(EC.visibility_of_element_located(loc(k))).send_keys(t)

        def login():
            driver.get(config.BASE_URL)
            type_("login_user", config.USERNAME)
            type_("login_pass", config.PASSWORD)
            click("login_submit")
            wait.until(EC.visibility_of_element_located(loc("crear_reserva")))

        def reservas():
            click("crear_reserva")

        def sucursal():
            if config.SUCURSAL:
                el = wait.until(EC.presence_of_element_located(loc("sucursal_select")))
                Select(el).select_by_visible_text(config.SUCURSAL)

        def buscar():
            click("tab_hoteles")
            type_("destino", config.DESTINO)
            click("buscar")
            wait.until(EC.presence_of_element_located(loc("resultado_hotel")))
            n = len(driver.find_elements(*loc("resultado_hotel")))
            bus.emit("info", message=f"Hoteles encontrados: {n}")

        def seleccionar():
            click("primer_reservar")

        def pago():
            wait.until(EC.visibility_of_element_located(loc("modulo_pago")))

        for i, fn in enumerate([login, reservas, sucursal, buscar, seleccionar, pago]):
            step(i, fn)
        bus.emit("done", ok=True)

    except Exception as e:
        bus.emit("step", index=current if current is not None else 0,
                 name=STEPS[current or 0], status="error", error=str(e))
        bus.emit("done", ok=False, error=traceback.format_exc())
    finally:
        if net:
            import time; time.sleep(1); net.stop()
        if driver:
            input_hold = False  # pon True si quieres dejar el navegador abierto
            if not input_hold:
                driver.quit()
