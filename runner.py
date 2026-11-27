"""Flujo Selenium: login -> reserva -> búsqueda -> selección -> datos -> pago."""
import base64, traceback, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ElementClickInterceptedException, ElementNotInteractableException, NoSuchElementException, TimeoutException

import config
from events import bus
from network import NetworkCollector
from recorder import ScreenRecorder

BY = {"css": By.CSS_SELECTOR, "xpath": By.XPATH, "id": By.ID}

# --- FLUJO VUELOS ---
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
    driver, net, rec = None, None, None
    current = None

    def step(i, fn):
        nonlocal current
        current = i
        bus.emit("step", index=i, name=STEPS[i], status="running")
        fn()
        # --- PROTECCIÓN PARA LA CAPTURA ---
        shot = None
        try:
            png = driver.get_screenshot_as_png()
            if png:
                shot = base64.b64encode(png).decode()
        except Exception as e:
            bus.emit("info", message=f"No se pudo tomar captura en el paso {i}: {e}")
        # ----------------------------------
        bus.emit("step", index=i, name=STEPS[i], status="ok", screenshot=shot)

    try:
        driver = build_driver()
        net = NetworkCollector(driver)
        net.start()

        # --- GRABACIÓN DE VIDEO ---
        rec = ScreenRecorder(filename=f"aereo_{int(time.time())}", fps=6, driver=driver)
        rec.start()
        bus.emit("recording_started")
        
        # --- FUNCIONES BLINDADAS ---
        def esperar_elemento(key, tiempo=None):
            t = tiempo if tiempo else config.TIEMPO_ESPERA
            return WebDriverWait(driver, t).until(EC.presence_of_element_located(loc(key)))

        def click_seguro(key):
            el = esperar_elemento(key)
            try:
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable(loc(key))).click()
            except (ElementClickInterceptedException, ElementNotInteractableException, TimeoutException):
                driver.execute_script("arguments[0].scrollIntoView(true);", el)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", el)
            time.sleep(1)

        def entrar_frame_seguro(frame_id):
            WebDriverWait(driver, config.TIEMPO_ESPERA).until(EC.frame_to_be_available_and_switch_to_it((By.ID, frame_id)))

        def volver_al_inicio():
            driver.switch_to.default_content()

        def reconectar_iframe():
            volver_al_inicio()
            entrar_frame_seguro(config.FRAME_TAB_1)
            entrar_frame_seguro(config.FRAME_FLOW)
            time.sleep(1)

        # 1) Login
        def login():
            driver.get(config.BASE_URL)
            esperar_elemento("login_user").send_keys(config.USERNAME)
            esperar_elemento("login_pass").send_keys(config.PASSWORD)
            esperar_elemento("login_service").send_keys(config.SERVICE)
            click_seguro("login_submit")
            WebDriverWait(driver, config.TIEMPO_ESPERA).until(lambda d: "Login.aspx" not in d.current_url)
            time.sleep(2) 

        # 2) Crear Reserva
        def reservas():
            volver_al_inicio()
            click_seguro("crear_reserva")
            try:
                modal_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(loc("seguir_sin_cliente")))
                driver.execute_script("arguments[0].click();", modal_btn)
                time.sleep(5) 
            except TimeoutException:
                pass
            volver_al_inicio()
            entrar_frame_seguro(config.FRAME_TAB_0)
            entrar_frame_seguro(config.FRAME_FLOW)
            
            try:
                WebDriverWait(driver, 5).until(EC.visibility_of_element_located(loc("login_user")))
                esperar_elemento("login_user").send_keys(config.USERNAME)
                esperar_elemento("login_pass").send_keys(config.PASSWORD)
                esperar_elemento("login_service").send_keys(config.SERVICE)
                click_seguro("login_submit")
                time.sleep(4)
                volver_al_inicio()
                entrar_frame_seguro(config.FRAME_TAB_0)
                entrar_frame_seguro(config.FRAME_FLOW)
            except TimeoutException:
                pass

        # 3) Sucursal
        def sucursal():
            click_seguro("tab_aereos")
            time.sleep(3) 
            box = esperar_elemento("sucursal_single", 15)
            if "PracticanteAutoma" not in box.text:
                driver.execute_script("arguments[0].scrollIntoView(true);", box)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", box)
                time.sleep(1.5) 
                search_input = esperar_elemento("sucursal_search", 10)
                search_input.send_keys("PracticanteAutoma")
                time.sleep(1.5) 
                search_input.send_keys(Keys.TAB)
                time.sleep(1.5)

        # 4) Buscar Vuelos
        def buscar():
            volver_al_inicio()
            entrar_frame_seguro(config.FRAME_TAB_0)
            entrar_frame_seguro(config.FRAME_FLOW)
            
            WebDriverWait(driver, 30).until(EC.visibility_of_element_located(loc("origen")))
            
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
            
            start_date = esperar_elemento("fecha_ida")
            driver.execute_script(f"arguments[0].value = '{config.FECHA_IDA}';", start_date)
            end_date = esperar_elemento("fecha_vuelta")
            driver.execute_script(f"arguments[0].value = '{config.FECHA_VUELTA}';", end_date)
            time.sleep(1)
            
            try:
                Select(driver.find_element(*loc("adultos"))).select_by_value(config.ADULTOS)
            except Exception: 
                pass
            
            click_seguro("buscar_aereo")
            time.sleep(10) 
            reconectar_iframe()
            
            esperar_elemento("resultado_ida", 60)

        # 5) Seleccionar Vuelos
        def seleccionar():
            el_ida = esperar_elemento("resultado_ida")
            driver.execute_script("arguments[0].scrollIntoView(true);", el_ida)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", el_ida)
            time.sleep(2)
            try: 
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
            Select(esperar_elemento("pax_titulo")).select_by_value("0") 
            esperar_elemento("pax_nombre").send_keys(config.PAX_NOMBRE)
            esperar_elemento("pax_apellido").send_keys(config.PAX_APELLIDO)
            esperar_elemento("pax_documento").send_keys(config.PAX_DOC)
            
            nac = esperar_elemento("pax_nacionalidad")
            nac.clear()
            nac.send_keys(config.PAX_NACIONALIDAD)
            time.sleep(2)
            try:
                opt_nac = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "ul.ui-autocomplete li:first-child")))
                driver.execute_script("arguments[0].click();", opt_nac)
            except TimeoutException:
                nac.send_keys(Keys.ARROW_DOWN)
                nac.send_keys(Keys.TAB)
            time.sleep(1.5) 
            
            try:
                Select(esperar_elemento("pax_dob_dia", 5)).select_by_value("1")
                time.sleep(0.5)
                Select(esperar_elemento("pax_dob_mes", 5)).select_by_value("1")
                time.sleep(0.5)
                Select(esperar_elemento("pax_dob_anio", 5)).select_by_value("1990")
            except Exception:
                pass

            esperar_elemento("pax_email").send_keys(config.PAX_EMAIL)
            esperar_elemento("pax_telefono").send_keys(config.PAX_TELEFONO)
            click_seguro("chk_terminos")
            click_seguro("btn_continuar_datos")
            time.sleep(4)

        # 8) Módulo de Pago
        def pago():
            reconectar_iframe()
            esperar_elemento("btn_pagar", 30)

        for i, fn in enumerate([login, reservas, sucursal, buscar, seleccionar, confirmar, datos, pago]):
            step(i, fn)
        bus.emit("done", ok=True)

    except Exception as e:
        idx = current if current is not None else 0
        bus.emit("step", index=idx, name=STEPS[idx], status="error", error=str(e))
        bus.emit("done", ok=False, error=traceback.format_exc())
    finally:
        # --- DETENER GRABACIÓN ---
        if rec:
            rec.stop()
            video_url = rec.get_video_url()
            bus.emit("recording_stopped", video_url=video_url)

        if net:
            time.sleep(1)
            net.stop()
        if driver:
            MANTENER_ABIERTO_PARA_DEBUG = True 
            if not MANTENER_ABIERTO_PARA_DEBUG:
                driver.quit()
            else:
                bus.emit("info", message="Navegador mantenido abierto. Ciérralo manualmente para liberar el proceso.")
                while True:
                    time.sleep(1)
                    try:
                        driver.title 
                    except Exception:
                        break


# ==========================================
# --- FLUJO HOTELES ---
# ==========================================
HOTEL_STEPS = [
    "Preparar reserva (Hotel)",
    "Buscar hoteles",
    "Filtrar y seleccionar hotel",
    "Datos del pasajero (Hotel)",
    "Módulo de pago (Hotel)"
]

def run_hotel():
    bus.emit("reset", steps=HOTEL_STEPS)
    driver, net, rec = None, None, None
    current = None

    def step(i, fn):
        nonlocal current
        current = i
        bus.emit("step", index=i, name=HOTEL_STEPS[i], status="running")
        fn()
        # --- PROTECCIÓN PARA LA CAPTURA ---
        shot = None
        try:
            png = driver.get_screenshot_as_png()
            if png:
                shot = base64.b64encode(png).decode()
        except Exception as e:
            bus.emit("info", message=f"No se pudo tomar captura en el paso {i}: {e}")
        # ----------------------------------
        bus.emit("step", index=i, name=HOTEL_STEPS[i], status="ok", screenshot=shot)

    try:
        driver = build_driver()
        net = NetworkCollector(driver)
        net.start()

        # --- GRABACIÓN DE VIDEO ---
        rec = ScreenRecorder(filename=f"hotel_{int(time.time())}", fps=6, driver=driver)
        rec.start()
        bus.emit("recording_started")
        
        # Funciones blindadas (reutilizables)
        def esperar_elemento(key, tiempo=None):
            t = tiempo if tiempo else config.TIEMPO_ESPERA
            return WebDriverWait(driver, t).until(EC.presence_of_element_located(loc(key)))

        def click_seguro(key):
            el = esperar_elemento(key)
            try:
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable(loc(key))).click()
            except (ElementClickInterceptedException, ElementNotInteractableException, TimeoutException):
                driver.execute_script("arguments[0].scrollIntoView(true);", el)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", el)
            time.sleep(1)

        def entrar_frame_seguro(frame_id):
            WebDriverWait(driver, config.TIEMPO_ESPERA).until(EC.frame_to_be_available_and_switch_to_it((By.ID, frame_id)))

        def volver_al_inicio():
            driver.switch_to.default_content()

        def reconectar_iframe():
            volver_al_inicio()
            entrar_frame_seguro(config.FRAME_TAB_1)
            entrar_frame_seguro(config.FRAME_FLOW)
            time.sleep(1)

        # 1) Preparar Reserva
        def preparar():
            driver.get(config.BASE_URL)
            esperar_elemento("login_user").send_keys(config.USERNAME)
            esperar_elemento("login_pass").send_keys(config.PASSWORD)
            esperar_elemento("login_service").send_keys(config.SERVICE)
            click_seguro("login_submit")
            WebDriverWait(driver, config.TIEMPO_ESPERA).until(lambda d: "Login.aspx" not in d.current_url)
            time.sleep(2) 
            
            volver_al_inicio()
            click_seguro("crear_reserva")
            try:
                modal_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(loc("seguir_sin_cliente")))
                driver.execute_script("arguments[0].click();", modal_btn)
                time.sleep(5) 
            except TimeoutException:
                pass
            
            volver_al_inicio()
            entrar_frame_seguro(config.FRAME_TAB_0)
            entrar_frame_seguro(config.FRAME_FLOW)
            
            try:
                WebDriverWait(driver, 5).until(EC.visibility_of_element_located(loc("login_user")))
                esperar_elemento("login_user").send_keys(config.USERNAME)
                esperar_elemento("login_pass").send_keys(config.PASSWORD)
                esperar_elemento("login_service").send_keys(config.SERVICE)
                click_seguro("login_submit")
                time.sleep(4)
                volver_al_inicio()
                entrar_frame_seguro(config.FRAME_TAB_0)
                entrar_frame_seguro(config.FRAME_FLOW)
            except TimeoutException:
                pass

        # 2) Buscar Hoteles
        def buscar_hotel():
            click_seguro("tab_hotel")
            time.sleep(3) 
            
            bus.emit("info", message="Seleccionando sucursal en el formulario de hotel...")
            box = esperar_elemento("sucursal_single", 15)
            if "PracticanteAutoma" not in box.text:
                driver.execute_script("arguments[0].scrollIntoView(true);", box)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", box)
                time.sleep(1.5) 
                search_input = esperar_elemento("sucursal_search", 10)
                search_input.send_keys("PracticanteAutoma")
                time.sleep(1.5) 
                search_input.send_keys(Keys.TAB)
                time.sleep(1.5)

            bus.emit("info", message="Ingresando ciudad destino...")
            dest = esperar_elemento("hotel_destino")
            dest.clear()
            dest.send_keys(config.HOTEL_DESTINO) 
            time.sleep(2)
            try:
                driver.find_element(By.CSS_SELECTOR, "ul.ui-autocomplete li:first-child").click()
            except:
                dest.send_keys(Keys.ARROW_DOWN)
                dest.send_keys(Keys.ENTER)
            time.sleep(1)

            bus.emit("info", message="Ingresando fechas...")
            checkin = esperar_elemento("hotel_checkin")
            driver.execute_script(f"arguments[0].value = '{config.HOTEL_FECHA_IDA}';", checkin)
            checkout = esperar_elemento("hotel_checkout")
            driver.execute_script(f"arguments[0].value = '{config.HOTEL_FECHA_VUELTA}';", checkout)
            driver.execute_script("arguments[0].blur();", checkout)
            time.sleep(2)

            bus.emit("info", message="Seleccionando cantidad de personas y habitaciones...")
            try:
                Select(esperar_elemento("hotel_habitaciones")).select_by_value(config.HOTEL_HABITACIONES)
                Select(esperar_elemento("hotel_adultos")).select_by_value(config.HOTEL_ADULTOS)
                Select(esperar_elemento("hotel_ninos")).select_by_value(config.HOTEL_NINOS)
            except Exception as e:
                bus.emit("info", message=f"Aviso seleccionando cantidades: {e}")

            bus.emit("info", message="Clic en Buscar Hoteles...")
            click_seguro("buscar_hotel")
            time.sleep(10) 
            
            reconectar_iframe()
            esperar_elemento("hotel_categoria_2_estrellas", 60)

        # 3) Seleccionar Hotel
        def seleccionar_hotel():
            reconectar_iframe()
            time.sleep(2)
            try:
                cat = esperar_elemento("hotel_categoria_2_estrellas", 10)
                if not cat.is_selected():
                    driver.execute_script("arguments[0].click();", cat)
                    time.sleep(2)
            except Exception:
                pass

            bus.emit("info", message="Seleccionando primer hotel de los resultados...")
            btn_sel = esperar_elemento("hotel_seleccionar", 20)
            driver.execute_script("arguments[0].scrollIntoView(true);", btn_sel)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", btn_sel)
            time.sleep(5) 

        # 4) Datos del Pasajero
        def datos_hotel():
            bus.emit("info", message="Ingresando datos del pasajero...")
            reconectar_iframe()
            time.sleep(3)
            
            Select(esperar_elemento("pax_titulo")).select_by_value("0") 
            esperar_elemento("pax_nombre").send_keys(config.PAX_NOMBRE)
            esperar_elemento("pax_apellido").send_keys(config.PAX_APELLIDO)
            esperar_elemento("pax_documento").send_keys(config.PAX_DOC)
            
            bus.emit("info", message="Ingresando nacionalidad...")
            nac = esperar_elemento("pax_nacionalidad")
            nac.clear()
            nac.send_keys(config.PAX_NACIONALIDAD)
            time.sleep(2)
            try:
                opt_nac = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "ul.ui-autocomplete li:first-child")))
                driver.execute_script("arguments[0].click();", opt_nac)
            except TimeoutException:
                nac.send_keys(Keys.ARROW_DOWN)
                nac.send_keys(Keys.TAB)
            time.sleep(1.5) 
            
            bus.emit("info", message="Ingresando fecha de nacimiento...")
            try:
                Select(esperar_elemento("pax_dob_dia", 5)).select_by_value("1")
                time.sleep(0.5)
                Select(esperar_elemento("pax_dob_mes", 5)).select_by_value("1")
                time.sleep(0.5)
                Select(esperar_elemento("pax_dob_anio", 5)).select_by_value("1990")
            except Exception:
                pass

            bus.emit("info", message="Ingresando datos de contacto...")
            esperar_elemento("pax_email").send_keys(config.PAX_EMAIL)
            esperar_elemento("pax_telefono").send_keys(config.PAX_TELEFONO)
            
            bus.emit("info", message="Aceptando términos y continuando...")
            click_seguro("chk_terminos")
            click_seguro("btn_continuar_datos")
            time.sleep(5)

        # 5) Módulo de Pago
        def pago_hotel():
            bus.emit("info", message="Esperando módulo de pago de hotel...")
            reconectar_iframe()
            esperar_elemento("btn_pagar", 30)
            bus.emit("info", message="¡Módulo de pago de hotel alcanzado con éxito!")

        # Ejecutar pasos
        step(0, preparar)
        step(1, buscar_hotel)
        step(2, seleccionar_hotel)
        step(3, datos_hotel)
        step(4, pago_hotel)
        bus.emit("done", ok=True)

    except Exception as e:
        idx = current if current is not None else 0
        bus.emit("step", index=idx, name=HOTEL_STEPS[idx], status="error", error=str(e))
        bus.emit("done", ok=False, error=traceback.format_exc())
    finally:
        # --- DETENER GRABACIÓN ---
        if rec:
            rec.stop()
            video_url = rec.get_video_url()
            bus.emit("recording_stopped", video_url=video_url)

        if net:
            time.sleep(1)
            net.stop()
        if driver:
            MANTENER_ABIERTO_PARA_DEBUG = True 
            if not MANTENER_ABIERTO_PARA_DEBUG:
                driver.quit()
            else:
                bus.emit("info", message="Navegador de Hotel mantenido abierto. Ciérralo manualmente.")
                while True:
                    time.sleep(1)
                    try:
                        driver.title
                    except Exception:
                        break