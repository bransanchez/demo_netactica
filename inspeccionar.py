"""Ayudante para encontrar selectores (no guarda el valor de campos de contraseña).
Uso:  python inspeccionar.py
1. Se abre Chrome en la URL de config.BASE_URL.
2. Navega a mano hasta la pantalla que quieras.
3. Vuelve a la terminal, escribe un nombre para esa pantalla y pulsa Enter.
4. Se guarda selectores_<nombre>.txt con los elementos de esa pantalla.
Escribe 'salir' para terminar."""
from selenium import webdriver
from selenium.webdriver.common.by import By
import config

JS = """
return Array.from(document.querySelectorAll('input,button,select,textarea,a,[onclick]'))
 .filter(e => e.offsetParent !== null)
 .map(e => ({tag:e.tagName.toLowerCase(), id:e.id, name:e.name||'', type:e.type||'',
   text:(e.type==='password' ? '' : (e.innerText||e.value||'')).trim().slice(0,40),
   ph:e.placeholder||'',
   cls:(e.className&&e.className.toString().slice(0,50))||''}));
"""

def corto(ex):
    return str(ex).split("\n")[0][:120]

def volcar(driver, path, lines):
    titulo = "Página principal" if not path else "IFRAME " + " > ".join(map(str, path))
    lines.append(f"\n=== {titulo} ===")
    try:
        for e in driver.execute_script(JS):
            lines.append(f"{e['tag']:8} id={e['id']!r} name={e['name']!r} type={e['type']!r} "
                         f"texto={e['text']!r} placeholder={e['ph']!r} class={e['cls']!r}")
    except Exception as ex:
        lines.append(f"(no se pudo leer este contexto: {corto(ex)})")
        return

    frames = driver.find_elements(By.CSS_SELECTOR, "iframe,frame")
    for i, f in enumerate(frames):
        try:
            info = (f"id={f.get_attribute('id')!r} name={f.get_attribute('name')!r} "
                    f"src={(f.get_attribute('src') or '')[:80]!r} visible={f.is_displayed()}")
        except Exception:
            info = "(sin info)"
        lines.append(f"\n-- iframe {path + [i]}: {info}")
        try:
            driver.switch_to.frame(i)
        except Exception as ex:
            lines.append(f"(iframe {path + [i]} no accesible: {corto(ex)})")
            continue
        try:
            volcar(driver, path + [i], lines)
        finally:
            driver.switch_to.parent_frame()

def dump(driver, path_archivo):
    lines = []
    driver.switch_to.default_content()
    volcar(driver, [], lines)
    driver.switch_to.default_content()
    with open(path_archivo, "w", encoding="utf-8") as fh:
        fh.write(f"URL: {driver.current_url}\n" + "\n".join(lines))
    print(f"Guardado: {path_archivo}  ({len(lines)} líneas)")

if __name__ == "__main__":
    d = webdriver.Chrome()
    d.maximize_window()
    d.get(config.BASE_URL)
    while True:
        nombre = input("\nNombre de esta pantalla (o 'salir'): ").strip()
        if nombre.lower() == "salir":
            break
        dump(d, f"selectores_{nombre or 'pantalla'}.txt")
    d.quit()