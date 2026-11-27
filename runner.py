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
        net = NetworkCollector(driver)
        net.start()
        
        # --- FUNCIONES BLINDADAS ---
        def esperar_elemento(key, tiempo=None):
            t = tiempo if tiempo else config.TIEMPO_ESPERA
            return WebDriverWait(driver, t).until(
                EC.presence_of_element_located(loc(key))
            )

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
            el_user = esperar_elemento("login_user")
            el_user.clear()
            el_user.send_keys(config.USERNAME)
            
            el_pass = esperar_elemento("login_pass")
            el_pass.clear()
            el_pass.send_keys(config.PASSWORD)
            
            el_serv = esperar_elemento("login_service")
            el_serv.clear()
            el_serv.send_keys(config.SERVICE)
            
            click_seguro("login_submit")
            
            WebDriverWait(driver, config.TIEMPO_ESPERA).until(
                lambda d: "Login.aspx" not in d.current_url
            )
            time.sleep(2) 

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
            
            bus.emit("info", message="Seleccionando tratamiento (Sr)...")
            sel_titulo = Select(esperar_elemento("pax_titulo"))
            sel_titulo.select_by_value("0") 
            
            el_name = esperar_elemento("pax_nombre")
            el_name.send_keys(config.PAX_NOMBRE)
            el_last = esperar_elemento("pax_apellido")
            el_last.send_keys(config.PAX_APELLIDO)
            
            el_doc = esperar_elemento("pax_documento")
            el_doc.send_keys(config.PAX_DOC)
            
            bus.emit("info", message="Escribiendo nacionalidad y seleccionando...")
            nac = esperar_elemento("pax_nacionalidad")
            nac.clear()
            nac.send_keys(config.PAX_NACIONALIDAD)
            
            bus.emit("info", message="Esperando que cargue el menú de nacionalidad...")
            try:
                opt_nac = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "ul.ui-autocomplete li:first-child"))
                )
                driver.execute_script("arguments[0].click();", opt_nac)
                bus.emit("info", message="Nacionalidad seleccionada del menú.")
            except TimeoutException:
                bus.emit("info", message="No salió el menú. Usando TAB...")
                nac.send_keys(Keys.ARROW_DOWN)
                nac.send_keys(Keys.TAB)
            
            time.sleep(1.5) 

            bus.emit("info", message="Llenando fecha de nacimiento...")
            try:
                Select(esperar_elemento("pax_dob_dia", 5)).select_by_value("1")
                time.sleep(0.5)
                Select(esperar_elemento("pax_dob_mes", 5)).select_by_value("1")
                time.sleep(0.5)
                Select(esperar_elemento("pax_dob_anio", 5)).select_by_value("1990")
            except Exception as e:
                bus.emit("info", message=f"No se pudo llenar la fecha de nacimiento (puede que sea opcional): {e}")

            el_mail = esperar_elemento("pax_email")
            el_mail.send_keys(config.PAX_EMAIL)
            el_phone = esperar_elemento("pax_telefono")
            el_phone.send_keys(config.PAX_TELEFONO)
            
            click_seguro("chk_terminos")
            click_seguro("btn_continuar_datos")
            time.sleep(4)

        # 8) Módulo de Pago
        def pago():
            reconectar_iframe()
            esperar_elemento("btn_pagar", 30)
            bus.emit("info", message="¡Módulo de pago alcanzado con éxito!")

         # --- HOTEL (PREPARACIÓN) ---

        
            def buscar_hotel():

                bus.emit(
                "info",
                 message="HOTEL: búsqueda pendiente de implementación"
             )


            def seleccionar_hotel():

             bus.emit(
            "info",
            message="HOTEL: selección pendiente de implementación"
            )


            def confirmar_hotel():

             bus.emit(
            "info",
             message="HOTEL: confirmación pendiente de implementación"
            )


            def run_hotel_demo():

                buscar_hotel()

                seleccionar_hotel()

                confirmar_hotel()   



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
            MANTENER_ABIERTO_PARA_DEBUG = False 
            if not MANTENER_ABIERTO_PARA_DEBUG:
                driver.quit()


HOTEL_STEPS = [
    "Preparar reserva",
    "Buscar hoteles",
    "Filtrar y seleccionar hotel",
    "Confirmar selección de hotel",
]


def _hotel_log(paso, iframe, message):
    bus.emit(
        "info",
        message=f"HOTEL | paso={paso} | iframe={iframe} | {message}",
    )


def esperar_elemento(driver, key, tiempo=None, paso="HOTEL", iframe="contexto actual"):
    timeout = tiempo if tiempo else config.TIEMPO_ESPERA
    selector = config.SEL[key]
    _hotel_log(
        paso,
        iframe,
        f"Esperando selector '{key}'={selector!r} (timeout={timeout}s).",
    )
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(loc(key))
        )
    except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as error:
        _hotel_log(
            paso,
            iframe,
            f"Fallo esperando selector '{key}'={selector!r}: "
            f"{type(error).__name__}: {error}",
        )
        raise
    _hotel_log(paso, iframe, f"Selector '{key}' encontrado.")
    return element


def click_seguro(driver, key, paso="HOTEL", iframe="contexto actual"):
    selector = config.SEL[key]
    element = esperar_elemento(driver, key, paso=paso, iframe=iframe)
    _hotel_log(paso, iframe, f"Esperando que el selector '{key}'={selector!r} sea clicable.")
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(loc(key))
        ).click()
    except ElementClickInterceptedException as error:
        _hotel_log(
            paso,
            iframe,
            f"ElementClickInterceptedException en selector '{key}'={selector!r}: "
            f"{error}. Se conserva el fallback JS existente.",
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", element)
    except ElementNotInteractableException as error:
        _hotel_log(
            paso,
            iframe,
            f"ElementNotInteractableException en selector '{key}'={selector!r}: "
            f"{error}. Se conserva el fallback JS existente.",
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", element)
    except TimeoutException as error:
        _hotel_log(
            paso,
            iframe,
            f"TimeoutException esperando/clicando selector '{key}'={selector!r}: {error}",
        )
        raise
    except NoSuchElementException as error:
        _hotel_log(
            paso,
            iframe,
            f"NoSuchElementException en selector '{key}'={selector!r}: {error}",
        )
        raise
    _hotel_log(paso, iframe, f"Clic completado para selector '{key}'.")
    time.sleep(1)


def entrar_frame_seguro(driver, frame_id, paso="HOTEL", iframe="contexto actual"):
    _hotel_log(
        paso,
        iframe,
        f"Verificando iframe por ID '{frame_id}' antes de cambiar de contexto.",
    )
    try:
        frame_element = WebDriverWait(driver, config.TIEMPO_ESPERA).until(
            EC.presence_of_element_located((By.ID, frame_id))
        )
        actual_id = frame_element.get_attribute("id")
        if actual_id != frame_id:
            raise RuntimeError(
                f"Se esperaba iframe id='{frame_id}', se encontró id='{actual_id}'."
            )
        _hotel_log(
            paso,
            iframe,
            f"ID de iframe verificado: '{actual_id}'. Cambiando al iframe.",
        )
        WebDriverWait(driver, config.TIEMPO_ESPERA).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, frame_id))
        )
    except (TimeoutException, NoSuchElementException) as error:
        _hotel_log(
            paso,
            iframe,
            f"Fallo verificando/entrando al iframe id='{frame_id}': "
            f"{type(error).__name__}: {error}",
        )
        raise
    _hotel_log(paso, frame_id, f"Contexto activo confirmado en iframe id='{frame_id}'.")


def reconectar_iframe(driver, tab_frame, paso="HOTEL"):
    _hotel_log(
        paso,
        "default_content",
        f"Reiniciando contexto para verificar {tab_frame} > {config.FRAME_FLOW}.",
    )
    driver.switch_to.default_content()
    entrar_frame_seguro(driver, tab_frame, paso=paso, iframe="default_content")
    entrar_frame_seguro(driver, config.FRAME_FLOW, paso=paso, iframe=tab_frame)
    time.sleep(1)
    _hotel_log(
        paso,
        f"{tab_frame} > {config.FRAME_FLOW}",
        "Ambos iframes están disponibles y el contexto interno quedó activo.",
    )


def _esperar_hotel_clicable(driver, key, paso, iframe):
    selector = config.SEL[key]
    _hotel_log(
        paso,
        iframe,
        f"Esperando clicabilidad del selector '{key}'={selector!r}.",
    )
    try:
        element = WebDriverWait(driver, config.TIEMPO_ESPERA).until(
            EC.element_to_be_clickable(loc(key))
        )
    except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as error:
        _hotel_log(
            paso,
            iframe,
            f"Fallo esperando selector clicable '{key}'={selector!r}: "
            f"{type(error).__name__}: {error}",
        )
        raise
    _hotel_log(paso, iframe, f"Selector '{key}' está clicable.")
    return element


def _preparar_reserva_hotel(driver):
    paso = "Paso 0 - Preparar reserva"
    _hotel_log(paso, "navegador", f"Abriendo {config.BASE_URL}.")
    driver.get(config.BASE_URL)
    user = esperar_elemento(driver, "login_user", paso=paso, iframe="documento principal")
    user.clear()
    user.send_keys(config.USERNAME)
    _hotel_log(paso, "documento principal", "Usuario ingresado.")
    password = esperar_elemento(driver, "login_pass", paso=paso, iframe="documento principal")
    password.clear()
    password.send_keys(config.PASSWORD)
    _hotel_log(paso, "documento principal", "Contraseña ingresada.")
    service = esperar_elemento(driver, "login_service", paso=paso, iframe="documento principal")
    service.clear()
    service.send_keys(config.SERVICE)
    _hotel_log(paso, "documento principal", "Servicio ingresado.")
    click_seguro(driver, "login_submit", paso=paso, iframe="documento principal")
    _hotel_log(paso, "documento principal", "Enviado el formulario de acceso.")
    WebDriverWait(driver, config.TIEMPO_ESPERA).until(
        lambda current_driver: "Login.aspx" not in current_driver.current_url
    )
    time.sleep(2)

    driver.switch_to.default_content()
    _hotel_log(paso, "default_content", "Acceso completado; iniciando Crear reserva.")
    click_seguro(driver, "crear_reserva", paso=paso, iframe="documento principal")
    try:
        modal_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(loc("seguir_sin_cliente"))
        )
        driver.execute_script("arguments[0].click();", modal_button)
        _hotel_log(paso, "documento principal", "Confirmado continuar sin cliente.")
        time.sleep(5)
    except TimeoutException:
        _hotel_log(paso, "documento principal", "No apareció el diálogo de cliente; se continúa.")

    reconectar_iframe(driver, config.FRAME_TAB_0, paso=paso)
    try:
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located(loc("login_user"))
        )
        _hotel_log(
            paso,
            f"{config.FRAME_TAB_0} > {config.FRAME_FLOW}",
            "Se detectó login dentro del iframe.",
        )
        user = esperar_elemento(
            driver,
            "login_user",
            paso=paso,
            iframe=f"{config.FRAME_TAB_0} > {config.FRAME_FLOW}",
        )
        user.send_keys(config.USERNAME)
        password = esperar_elemento(
            driver,
            "login_pass",
            paso=paso,
            iframe=f"{config.FRAME_TAB_0} > {config.FRAME_FLOW}",
        )
        password.send_keys(config.PASSWORD)
        service = esperar_elemento(
            driver,
            "login_service",
            paso=paso,
            iframe=f"{config.FRAME_TAB_0} > {config.FRAME_FLOW}",
        )
        service.send_keys(config.SERVICE)
        click_seguro(
            driver,
            "login_submit",
            paso=paso,
            iframe=f"{config.FRAME_TAB_0} > {config.FRAME_FLOW}",
        )
        _hotel_log(
            paso,
            f"{config.FRAME_TAB_0} > {config.FRAME_FLOW}",
            "Login interno completado.",
        )
        time.sleep(4)
        reconectar_iframe(driver, config.FRAME_TAB_0, paso=paso)
    except TimeoutException:
        _hotel_log(
            paso,
            f"{config.FRAME_TAB_0} > {config.FRAME_FLOW}",
            "No apareció login interno; se continúa.",
        )


def buscar_hotel(driver):
    paso = "Paso 1 - Buscar hoteles"
    form_iframe = f"{config.FRAME_TAB_0} > {config.FRAME_FLOW}"
    results_iframe = f"{config.FRAME_TAB_1} > {config.FRAME_FLOW}"
    _hotel_log(paso, "default_content", "Conectando con el formulario HOTEL.")
    reconectar_iframe(driver, config.FRAME_TAB_0, paso=paso)
    click_seguro(driver, "tab_hotel", paso=paso, iframe=form_iframe)
    _hotel_log(paso, form_iframe, "Pestaña Hoteles abierta.")

    destination = esperar_elemento(
        driver, "hotel_destino", paso=paso, iframe=form_iframe
    )
    destination.clear()
    destination.send_keys(config.HOTEL_DESTINO)
    _hotel_log(paso, form_iframe, f"Destino ingresado: {config.HOTEL_DESTINO}.")
    destination.send_keys(Keys.ARROW_DOWN)
    destination.send_keys(Keys.ENTER)
    _hotel_log(paso, form_iframe, "Destino confirmado con teclado.")

    # Se conservan las fechas que carga el formulario; no se proporcionaron fechas nuevas.
    esperar_elemento(driver, "hotel_checkin", paso=paso, iframe=form_iframe)
    esperar_elemento(driver, "hotel_checkout", paso=paso, iframe=form_iframe)
    _hotel_log(paso, form_iframe, "Fechas cargadas por el formulario conservadas.")
    Select(
        esperar_elemento(
            driver, "hotel_habitaciones", paso=paso, iframe=form_iframe
        )
    ).select_by_value(config.HOTEL_HABITACIONES)
    _hotel_log(paso, form_iframe, f"Habitaciones={config.HOTEL_HABITACIONES}.")
    Select(
        esperar_elemento(driver, "hotel_adultos", paso=paso, iframe=form_iframe)
    ).select_by_value(config.HOTEL_ADULTOS)
    _hotel_log(paso, form_iframe, f"Adultos={config.HOTEL_ADULTOS}.")
    Select(
        esperar_elemento(driver, "hotel_ninos", paso=paso, iframe=form_iframe)
    ).select_by_value(config.HOTEL_NINOS)
    _hotel_log(paso, form_iframe, f"Niños={config.HOTEL_NINOS}.")

    _hotel_log(
        paso,
        form_iframe,
        (
            f"HOTEL: buscando en {config.HOTEL_DESTINO} "
            f"({config.HOTEL_HABITACIONES} habitación, "
            f"{config.HOTEL_ADULTOS} adulto, {config.HOTEL_NINOS} niños)."
        ),
    )
    click_seguro(driver, "buscar_hotel", paso=paso, iframe=form_iframe)
    _hotel_log(paso, form_iframe, "Búsqueda hotel enviada.")
    _hotel_log(
        paso,
        "default_content",
        "Después de buscar, verificando los iframes de resultados.",
    )
    reconectar_iframe(driver, config.FRAME_TAB_1, paso=paso)
    esperar_elemento(
        driver,
        "hotel_categoria_2_estrellas",
        paso=paso,
        iframe=results_iframe,
    )
    _hotel_log(
        paso,
        results_iframe,
        "Filtro de categoría localizado después de verificar ambos iframes.",
    )


def seleccionar_hotel(driver):
    paso = "Paso 2 - Filtrar y seleccionar hotel"
    iframe = f"{config.FRAME_TAB_1} > {config.FRAME_FLOW}"
    category_key = "hotel_categoria_2_estrellas"
    select_key = "hotel_seleccionar"

    _hotel_log(paso, "default_content", "Iniciando filtrado y selección.")
    reconectar_iframe(driver, config.FRAME_TAB_1, paso=paso)

    category = esperar_elemento(
        driver, category_key, paso=paso, iframe=iframe
    )
    try:
        category_selected = category.is_selected()
    except NoSuchElementException as error:
        _hotel_log(
            paso,
            iframe,
            f"NoSuchElementException al consultar selector "
            f"'{category_key}'={config.SEL[category_key]!r}: {error}",
        )
        raise
    _hotel_log(
        paso,
        iframe,
        f"Estado inicial del selector '{category_key}': "
        f"is_selected()={category_selected}.",
    )

    if not category_selected:
        _esperar_hotel_clicable(driver, category_key, paso, iframe)
        click_seguro(driver, category_key, paso=paso, iframe=iframe)
        _hotel_log(paso, iframe, "Clic de categoría 2 estrellas ejecutado.")
        _hotel_log(
            paso,
            iframe,
            f"Verificando selección del selector '{category_key}'="
            f"{config.SEL[category_key]!r}.",
        )
        try:
            WebDriverWait(driver, config.TIEMPO_ESPERA).until(
                lambda current_driver: current_driver.find_element(
                    *loc(category_key)
                ).is_selected()
            )
        except (TimeoutException, NoSuchElementException) as error:
            _hotel_log(
                paso,
                iframe,
                f"Fallo verificando selector '{category_key}'="
                f"{config.SEL[category_key]!r}: "
                f"{type(error).__name__}: {error}",
            )
            raise
        _hotel_log(paso, iframe, "Filtro de 2 estrellas confirmado.")
    else:
        _hotel_log(paso, iframe, "Filtro de 2 estrellas ya estaba seleccionado.")

    _esperar_hotel_clicable(driver, select_key, paso, iframe)
    _hotel_log(
        paso,
        iframe,
        f"Pulsando el primer resultado con selector "
        f"'{select_key}'={config.SEL[select_key]!r}.",
    )
    click_seguro(driver, select_key, paso=paso, iframe=iframe)
    _hotel_log(paso, iframe, "Clic en Seleccionar completado.")


def confirmar_hotel(driver):
    bus.emit(
        "info",
        message="HOTEL: se completó el clic en Seleccionar del primer resultado.",
    )


def run_hotel():
    bus.emit("reset", steps=HOTEL_STEPS)
    driver, net = None, None
    current = None

    def report_error(error):
        index = current if current is not None else 0
        step_name = f"Paso {index} - {HOTEL_STEPS[index]}"
        runner_frames = [
            frame
            for frame in traceback.extract_tb(error.__traceback__)
            if frame.filename == __file__
        ]
        if runner_frames:
            frame = runner_frames[-1]
            location = f"{frame.filename}:{frame.lineno} ({frame.name})"
        else:
            location = "línea de runner.py no disponible"
        if index == 2:
            iframe = f"{config.FRAME_TAB_1} > {config.FRAME_FLOW}"
        elif index == 1:
            iframe = (
                f"{config.FRAME_TAB_0} > {config.FRAME_FLOW} o "
                f"{config.FRAME_TAB_1} > {config.FRAME_FLOW}; revisar último "
                "evento de reconexión"
            )
        else:
            iframe = "revisar último evento de iframe"
        _hotel_log(
            step_name,
            iframe,
            f"{type(error).__name__} en {location}: {error}",
        )
        bus.emit(
            "step",
            index=index,
            name=HOTEL_STEPS[index],
            status="error",
            error=f"{type(error).__name__}: {error} ({location})",
        )
        bus.emit("done", ok=False, error=traceback.format_exc())

    def step(index, function):
        nonlocal current
        current = index
        bus.emit(
            "step",
            index=index,
            name=HOTEL_STEPS[index],
            status="running",
        )
        function()
        screenshot = base64.b64encode(driver.get_screenshot_as_png()).decode()
        bus.emit(
            "step",
            index=index,
            name=HOTEL_STEPS[index],
            status="ok",
            screenshot=screenshot,
        )

    try:
        driver = build_driver()
        net = NetworkCollector(driver)
        net.start()

        step(0, lambda: _preparar_reserva_hotel(driver))
        step(1, lambda: buscar_hotel(driver))
        step(2, lambda: seleccionar_hotel(driver))
        step(3, lambda: confirmar_hotel(driver))
        bus.emit("done", ok=True)
    except TimeoutException as error:
        report_error(error)
    except NoSuchElementException as error:
        report_error(error)
    except ElementClickInterceptedException as error:
        report_error(error)
    except Exception as error:
        report_error(error)
    finally:
        if net:
            time.sleep(1)
            net.stop()
        if driver:
            driver.quit()