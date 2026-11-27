"""Configuración del demo. Ajusta URLs, selectores y credenciales."""
import os

# URL de Login (Página inicial)
BASE_URL = "https://preprod.netactica.com/NetAdmin/Login.aspx"

# --- TIEMPO DE ESPERA (en segundos) ---
TIEMPO_ESPERA = 90 

# Credenciales (por variables de entorno)
USERNAME = os.getenv("NETA_USER", "")
PASSWORD = os.getenv("NETA_PASS", "")
SERVICE  = os.getenv("NETA_SERVICE", "regresion")

# Datos de la búsqueda aérea
ORIGEN       = os.getenv("NETA_ORIGEN", "Bogotá")
DESTINO      = os.getenv("NETA_DESTINO", "Miami")
FECHA_IDA    = os.getenv("NETA_FECHA_IDA", "12-04-2027")
FECHA_VUELTA = os.getenv("NETA_FECHA_VUELTA", "19-04-2027")
ADULTOS      = os.getenv("NETA_ADULTOS", "1")

# Datos del Pasajero
PAX_NOMBRE       = os.getenv("NETA_PAX_NOMBRE", "Juan")
PAX_APELLIDO     = os.getenv("NETA_PAX_APELLIDO", "Perez")
PAX_DOC          = os.getenv("NETA_PAX_DOC", "123456789")
PAX_EMAIL        = os.getenv("NETA_PAX_EMAIL", "correo@prueba.com")
PAX_TELEFONO     = os.getenv("NETA_PAX_TELEFONO", "3001234567")
PAX_NACIONALIDAD = os.getenv("NETA_PAX_NAC", "Colombia")

# Nombres de los iframes anidados
FRAME_TAB_0 = "iframeTab_0"   
FRAME_TAB_1 = "iframeTab_1"   
FRAME_FLOW  = "ctl00_FlowIFrame" 

HEADLESS = False

SEL = {
    # --- LOGIN ---
    "login_user":    ("id", "Login_UserName"),
    "login_pass":    ("id", "Login_Password"),
    "login_service": ("id", "Login_UserService"),
    "login_submit":  ("id", "Login_btnLogin"),

    # --- PÁGINA PRINCIPAL ---
    "crear_reserva": ("id", "ctl00_ContentPlaceHolder1_MainMenuControl_btnCreateItinerary"),
    "seguir_sin_cliente": ("id", "ctl00_ContentPlaceHolder1_btnNewIineraryWithoutClient"),

    # --- FORMULARIO AÉREO ---
    "tab_aereos":   ("xpath", "//span[contains(text(), 'Aéreos')]"),
    "origen":       ("id", "ctl00_ctl00_NetSiteContentPlaceHolder_NetFulfillmentContentPlaceHolder_txtOrigin"),
    "destino":      ("id", "ctl00_ctl00_NetSiteContentPlaceHolder_NetFulfillmentContentPlaceHolder_txtDestination"),
    
    "fecha_ida":    ("id", "ctl00_ctl00_NetSiteContentPlaceHolder_NetFulfillmentContentPlaceHolder_txtStartDate"),
    "fecha_vuelta": ("id", "ctl00_ctl00_NetSiteContentPlaceHolder_NetFulfillmentContentPlaceHolder_txtEndDate"),
    "adultos":      ("id", "ctl00_ctl00_NetSiteContentPlaceHolder_NetFulfillmentContentPlaceHolder_ddlAdults"),
    "buscar_aereo": ("id", "ctl00_ctl00_NetSiteContentPlaceHolder_NetFulfillmentContentPlaceHolder_btnAirQuote"),
    
    # Sucursal
    "sucursal_single": ("css", "#ctl00_ctl00_NetSiteContentPlaceHolder_NetFulfillmentContentPlaceHolder_ddlBranches_chosen a.chosen-single"),
    "sucursal_search": ("css", "#ctl00_ctl00_NetSiteContentPlaceHolder_NetFulfillmentContentPlaceHolder_ddlBranches_chosen .chosen-search-input"),
    "sucursal_option": ("xpath", "//li[contains(@class, 'active-result') and contains(., 'PracticanteAutoma')]"),

    # --- RESULTADOS DE VUELO ---
    "resultado_ida":      ("id", "Air_0_sector_0_opt_0"),
    "resultado_vuelta":   ("id", "Air_0_sector_1_opt_0"),
    "seleccionar_vuelos": ("xpath", "//button[contains(normalize-space(.), 'Seleccionar Vuelos')]"),

    # --- CONFIRMACIÓN Y TARIFAS ---
    "btn_tarifa_basica": ("xpath", "(//a[contains(text(), 'Seleccionar')])[1]"), 
    "btn_seguir":        ("id", "btnContinue"),

    # --- DATOS DEL PASAJERO ---
    "pax_titulo":       ("id", "Travelers_0__Title"), 
    "pax_nombre":       ("id", "Travelers_0__FirstName"),
    "pax_apellido":     ("id", "Travelers_0__LastName"),
    "pax_documento":    ("id", "Travelers_0__DucumentNumber"),
    "pax_nacionalidad": ("id", "Travelers_0__Nationality"),
    "pax_dob_dia":      ("id", "Travelers[0].DOB_d"), 
    "pax_dob_mes":      ("id", "Travelers[0].DOB_m"), 
    "pax_dob_anio":     ("id", "Travelers[0].DOB_y"), 
    "pax_email":        ("id", "ContactEmail"),
    "pax_telefono":     ("id", "ContactPhone"),
    "chk_terminos":     ("id", "chkTermsAndConditions"),
    "btn_continuar_datos": ("id", "submitButtonId"),

    # --- MÓDULO DE PAGO ---
    "btn_pagar": ("xpath", "//input[contains(@id, 'btnPaymentMethodLOC')]"), 


    # --- HOTEL ---

    "tab_hotel": (None, None),

    "hotel_destino": (None, None),

    "hotel_checkin": (None, None),

    "hotel_checkout": (None, None),

    "hotel_adultos": (None, None),

    "hotel_habitaciones": (None, None),

    "buscar_hotel": (None, None),

    "hotel_resultado": (None, None),

    "hotel_seleccionar": (None, None),

    }

