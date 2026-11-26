<<<<<<< HEAD
"""Flujo Selenium: login -> sucursal -> búsqueda -> selección -> módulo de pago."""
import base64, time, traceback
=======
"""Flujo Selenium: login -> reserva -> búsqueda -> selección -> datos -> pago."""
import base64, traceback, time
>>>>>>> 125bbc6 (flujo aereo terminado, falta mostrar las peticiones en network)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ElementClickInterceptedException, ElementNotInteractableException, TimeoutException

import config
from events import bus
from network import NetworkCollector

BY = {"css": By.CSS_SELECTOR, "xpath": By.XPATH, "id": By.ID}

STEPS = [
    "Iniciar sesión",
    "Abrir módulo de reservas",
    "Seleccionar sucursal",
    "Buscar vuelos (aéreo)",
    "Seleccionar vuelo",
    "Confirmar tarifa",
    "Datos del pasajero",
    "Módulo de pago"
]


def build_driver():
    opts = webdriver.ChromeOptions()
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    if config.HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1440,900")
    d = webdriver.Chrome(options=opts)
    d.execute_cdp_cmd("Network.enable", {})
    return d


def loc(key):
    kind, val = config.SEL[key]
    if kind is None:
        raise RuntimeError(f"Selector '{key}' no configurado")
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
<<<<<<< HEAD
        net = NetworkCollector(driver)
        net.start()
        wait = WebDriverWait(driver, 30)
        click = lambda k: wait.until(EC.element_to_be_clickable(loc(k))).click()
        type_ = lambda k, t: wait.until(EC.visibility_of_element_located(loc(k))).send_keys(t)
=======
        net = NetworkCollector(driver); net.start()
        
        # --- FUNCIONES BLINDADAS ---
        
        def esperar_elemento(key, tiempo=None):
            t = tiempo if tiempo else config.TIEMPO_ESPERA
            return WebDriverWait(driver, t).until(
                EC.presence_of_element_located(loc(key))
            )
>>>>>>> 125bbc6 (flujo aereo terminado, falta mostrar las peticiones en network)

        def click_seguro(key):
            el = esperar_elemento(key)
            try:
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable(loc(key))).click()
            except (ElementClickInterceptedException, ElementNotInteractableException, TimeoutException):
                bus.emit("info", message=f"Elemento '{key}' bloqueado. Usando JS...")
                driver.execute_script("arguments[0].scrollIntoView(true);", el)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", el)
            time.sleep(1)

        def entrar_frame_seguro(frame_id):
            WebDriverWait(driver, config.TIEMPO_ESPERA).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, frame_id))
            )

        def volver_al_inicio():
            driver.switch_to.default_content()

        def reconectar_iframe():
            volver_al_inicio()
            entrar_frame_seguro(config.FRAME_TAB_1)
            entrar_frame_seguro(config.FRAME_FLOW)
            time.sleep(1)

        # --- PASOS DEL FLUJO ---

        # 1) Login
        def login():
            driver.get(config.BASE_URL)
<<<<<<< HEAD
            for key, val in [("login_user", config.USERNAME),
                             ("login_pass", config.PASSWORD),
                             ("login_service", config.SERVICE)]:
                el = wait.until(EC.visibility_of_element_located(loc(key)))
                el.clear()
                el.send_keys(val)
            click("login_submit")
            wait.until(lambda d: "Login.aspx" not in d.current_url)
=======
            el_user = esperar_elemento("login_user")
            el_user.send_keys(config.USERNAME)
            el_pass = esperar_elemento("login_pass")
            el_pass.send_keys(config.PASSWORD)
            el_serv = esperar_elemento("login_service")
            el_serv.send_keys(config.SERVICE)
            
            click_seguro("login_submit")
            
            WebDriverWait(driver, config.TIEMPO_ESPERA).until(
                lambda d: "Login.aspx" not in d.current_url
            )
            time.sleep(2) 
>>>>>>> 125bbc6 (flujo aereo terminado, falta mostrar las peticiones en network)

        # 2) Crear Reserva
        def reservas():
            volver_al_inicio()
            click_seguro("crear_reserva")
            
            try:
                modal_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(loc("seguir_sin_cliente"))
                )
                driver.execute_script("arguments[0].click();", modal_btn)
                time.sleep(5) 
            except TimeoutException:
                pass

            volver_al_inicio()
            entrar_frame_seguro(config.FRAME_TAB_0)
            entrar_frame_seguro(config.FRAME_FLOW)
            
            try:
                WebDriverWait(driver, 5).until(EC.visibility_of_element_located(loc("login_user")))
                el_user = esperar_elemento("login_user")
                el_user.send_keys(config.USERNAME)
                el_pass = esperar_elemento("login_pass")
                el_pass.send_keys(config.PASSWORD)
                el_serv = esperar_elemento("login_service")
                el_serv.send_keys(config.SERVICE)
                
                click_seguro("login_submit")
                time.sleep(4)
                volver_al_inicio()
                entrar_frame_seguro(config.FRAME_TAB_0)
                entrar_frame_seguro(config.FRAME_FLOW)
            except TimeoutException:
                pass

        # 3) Sucursal
        def sucursal():
            bus.emit("info", message="Haciendo clic en Aéreos...")
            click_seguro("tab_aereos")
            time.sleep(3) 

            bus.emit("info", message="Verificando estado de la sucursal...")
            box = esperar_elemento("sucursal_single", 15)
            
            if "PracticanteAutoma" not in box.text:
                bus.emit("info", message="Sucursal no seleccionada. Abriendo dropdown...")
                
                driver.execute_script("arguments[0].scrollIntoView(true);", box)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", box)
                time.sleep(1.5) 
                
                bus.emit("info", message="Escribiendo en el buscador de sucursal...")
                search_input = esperar_elemento("sucursal_search", 10)
                search_input.send_keys("PracticanteAutoma")
                time.sleep(1.5) 
                
                bus.emit("info", message="Presionando TAB para confirmar selección...")
                search_input.send_keys(Keys.TAB)
                time.sleep(1.5)
                
                bus.emit("info", message="Sucursal PracticanteAutoma seleccionada.")
            else:
                bus.emit("info", message="Sucursal ya estaba seleccionada por defecto.")

        # 4) Buscar Vuelos
        def buscar():
            volver_al_inicio()
            entrar_frame_seguro(config.FRAME_TAB_0)
            entrar_frame_seguro(config.FRAME_FLOW)
            
            bus.emit("info", message="Esperando formulario visible...")
            WebDriverWait(driver, 30).until(EC.visibility_of_element_located(loc("origen")))
            
            bus.emit("info", message="Escribiendo Origen...")
            org_input = esperar_elemento("origen")
            org_input.clear()
            org_input.send_keys(config.ORIGEN)
            time.sleep(2) 
            try:
                driver.find_element(By.CSS_SELECTOR, "ul.ui-autocomplete li:first-child").click()
            except:
                org_input.send_keys(Keys.ARROW_DOWN)
                org_input.send_keys(Keys.ENTER)
            time.sleep(1)
            
            bus.emit("info", message="Escribiendo Destino...")
            dst_input = esperar_elemento("destino")
            dst_input.clear()
            dst_input.send_keys(config.DESTINO)
            time.sleep(2)
            try:
                driver.find_element(By.CSS_SELECTOR, "ul.ui-autocomplete li:first-child").click()
            except:
                dst_input.send_keys(Keys.ARROW_DOWN)
                dst_input.send_keys(Keys.ENTER)
            time.sleep(1)
            
            bus.emit("info", message="Escribiendo fechas...")
            start_date = esperar_elemento("fecha_ida")
            driver.execute_script(f"arguments[0].value = '{config.FECHA_IDA}';", start_date)
            
            end_date = esperar_elemento("fecha_vuelta")
            driver.execute_script(f"arguments[0].value = '{config.FECHA_VUELTA}';", end_date)
            time.sleep(1)
            
            try:
                sel_adultos = Select(driver.find_element(*loc("adultos")))
                sel_adultos.select_by_value(config.ADULTOS)
            except Exception: 
                pass
            
            bus.emit("info", message="Clic en Buscar Aéreos...")
            click_seguro("buscar_aereo")
            
            time.sleep(10) 
            reconectar_iframe()
            
            esperar_elemento("resultado_ida", 60)
            n = len(driver.find_elements(By.CSS_SELECTOR, "input[id^='Air_']"))
            bus.emit("info", message=f"Resultados cargados ({n} opciones)")

        # 5) Seleccionar Vuelos
        def seleccionar():
            bus.emit("info", message="Seleccionando vuelo de ida...")
            el_ida = esperar_elemento("resultado_ida")
            driver.execute_script("arguments[0].scrollIntoView(true);", el_ida)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", el_ida)
            time.sleep(2)
            
            try: 
                bus.emit("info", message="Seleccionando vuelo de vuelta...")
                el_vuelta = esperar_elemento("resultado_vuelta", 5)
                driver.execute_script("arguments[0].click();", el_vuelta)
                time.sleep(2)
            except Exception: 
                pass
            
            click_seguro("seleccionar_vuelos")
            time.sleep(4) 

        # 6) Confirmar Tarifa
        def confirmar():
            reconectar_iframe()
            time.sleep(3)
            click_seguro("btn_tarifa_basica")
            time.sleep(2)
            click_seguro("btn_seguir")
            time.sleep(3)

        # 7) Datos del Pasajero
        def datos():
            reconectar_iframe()
            time.sleep(3)
            
            # 1. Seleccionar Título (Sr)
            bus.emit("info", message="Seleccionando tratamiento (Sr)...")
            sel_titulo = Select(esperar_elemento("pax_titulo"))
            sel_titulo.select_by_value("0") # "0" es el value de "Sr"
            
            # 2. Nombre y Apellido
            el_name = esperar_elemento("pax_nombre")
            el_name.send_keys(config.PAX_NOMBRE)
            el_last = esperar_elemento("pax_apellido")
            el_last.send_keys(config.PAX_APELLIDO)
            
            # 3. Documento
            el_doc = esperar_elemento("pax_documento")
            el_doc.send_keys(config.PAX_DOC)
            
            # 4. Nacionalidad (Escribir, esperar y HACER CLIC en la opción)
            bus.emit("info", message="Escribiendo nacionalidad y seleccionando...")
            nac = esperar_elemento("pax_nacionalidad")
            nac.clear()
            nac.send_keys(config.PAX_NACIONALIDAD)
            
            # Esperamos explícitamente a que la lista de sugerencias aparezca
            bus.emit("info", message="Esperando que cargue el menú de nacionalidad...")
            try:
                # Esperar hasta 10 seg a que aparezca la primera opción del autocompletado
                opt_nac = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "ul.ui-autocomplete li:first-child"))
                )
                # Hacer clic con JS para evitar bloqueos
                driver.execute_script("arguments[0].click();", opt_nac)
                bus.emit("info", message="Nacionalidad seleccionada del menú.")
            except TimeoutException:
                # Si por alguna razón no sale el menú, usamos el truco del TAB como respaldo
                bus.emit("info", message="No salió el menú. Usando TAB...")
                nac.send_keys(Keys.ARROW_DOWN)
                nac.send_keys(Keys.TAB)
            
            time.sleep(1.5) # Pausa para que el sistema valide

            # 5. Fecha de Nacimiento (Día, Mes, Año)
            bus.emit("info", message="Llenando fecha de nacimiento...")
            try:
                Select(esperar_elemento("pax_dob_dia", 5)).select_by_value("1")
                time.sleep(0.5)
                Select(esperar_elemento("pax_dob_mes", 5)).select_by_value("1")
                time.sleep(0.5)
                Select(esperar_elemento("pax_dob_anio", 5)).select_by_value("1990")
            except Exception as e:
                bus.emit("info", message=f"No se pudo llenar la fecha de nacimiento (puede que sea opcional): {e}")

            # 6. Email y Teléfono
            el_mail = esperar_elemento("pax_email")
            el_mail.send_keys(config.PAX_EMAIL)
            el_phone = esperar_elemento("pax_telefono")
            el_phone.send_keys(config.PAX_TELEFONO)
            
            # 7. Términos y Continuar
            click_seguro("chk_terminos")
            click_seguro("btn_continuar_datos")
            time.sleep(4)

        # 8) Módulo de Pago
        def pago():
            reconectar_iframe()
            esperar_elemento("btn_pagar", 30)
            bus.emit("info", message="¡Módulo de pago alcanzado con éxito!")

        # --- EJECUCIÓN ---
        for i, fn in enumerate([login, reservas, sucursal, buscar, seleccionar, confirmar, datos, pago]):
            step(i, fn)
        bus.emit("done", ok=True)

    except Exception as e:
        idx = current if current is not None else 0
        bus.emit("step", index=idx, name=STEPS[idx], status="error", error=str(e))
        bus.emit("done", ok=False, error=traceback.format_exc())
    finally:
        if net:
            time.sleep(1)
            net.stop()
        if driver:
<<<<<<< HEAD
            driver.quit()
=======
            MANTENER_ABIERTO_PARA_DEBUG = True 
            if not MANTENER_ABIERTO_PARA_DEBUG:
                driver.quit()
>>>>>>> 125bbc6 (flujo aereo terminado, falta mostrar las peticiones en network)
