"""
Automatización de descarga de transacciones desde Cupón Electrónico Copec.
Usa Playwright para navegar el sitio, solicitar el reporte y enviarlo por email.
"""

import asyncio
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright

# Configuración desde variables de entorno (GitHub Secrets)
COPEC_RUT = os.environ.get("COPEC_RUT", "")
COPEC_PASSWORD = os.environ.get("COPEC_PASSWORD", "")
REPORT_EMAIL = os.environ.get("REPORT_EMAIL", "acornejo@cindependencia.cl")
COPEC_URL = "https://cuponelectronico.copec.cl/default.aspx"


async def login(page):
    """Inicia sesión en Cupón Electrónico Copec."""
    print(f"[INFO] Navegando a {COPEC_URL}...")
    await page.goto(COPEC_URL, wait_until="networkidle", timeout=60000)

    # Buscar campos de login (RUT y Clave)
    rut_input = page.locator('input[id*="txtRut"], input[name*="Rut"], input[placeholder*="Rut"]').first
    pass_input = page.locator('input[type="password"]').first
    login_btn = page.locator('input[type="submit"], button[id*="btnIngresar"], input[id*="btnIngresar"]').first

    await rut_input.fill(COPEC_RUT)
    await pass_input.fill(COPEC_PASSWORD)
    await login_btn.click()

    # Esperar a que cargue la página principal
    await page.wait_for_load_state("networkidle", timeout=30000)
    print("[OK] Login exitoso.")


async def navigate_to_download(page):
    """Navega a Informes > Descarga Transacciones por Departamento."""
    print("[INFO] Navegando a Descarga Transacciones por Departamento...")

    # Hacer hover en menú "Informes"
    informes_menu = page.locator('a:has-text("Informes"), li:has-text("Informes") > a').first
    await informes_menu.hover()
    await page.wait_for_timeout(1000)

    # Click en "Descarga Transacciones por Departamento"
    descarga_link = page.locator('a:has-text("Descarga Transacciones por Departamento")').first
    await descarga_link.click()
    await page.wait_for_load_state("networkidle", timeout=30000)
    print("[OK] Página de descarga cargada.")


async def configure_and_download(page):
    """Configura los filtros y solicita la descarga."""
    now = datetime.now()
    current_month = now.strftime("%B %Y")  # Ej: "Marzo 2026"

    print(f"[INFO] Configurando descarga para: {current_month}")

    # Seleccionar tipo "Consumos" (radio button - generalmente ya seleccionado)
    consumos_radio = page.locator('input[type="radio"][id*="Consumos"], input[type="radio"]:first-of-type').first
    if await consumos_radio.is_visible():
        await consumos_radio.check()

    # Seleccionar producto "PD" (Petróleo Diesel)
    producto_select = page.locator('select[id*="Producto"], select[id*="producto"]').first
    if await producto_select.is_visible():
        # Intentar seleccionar por value o por texto
        try:
            await producto_select.select_option(label="PD")
        except Exception:
            try:
                await producto_select.select_option(value="PD")
            except Exception:
                # Buscar opción que contenga "PD"
                options = await producto_select.locator("option").all()
                for opt in options:
                    text = await opt.text_content()
                    if "PD" in text.upper():
                        value = await opt.get_attribute("value")
                        await producto_select.select_option(value=value)
                        break
        print("[OK] Producto PD seleccionado.")

    # Configurar Mes Inicio = mes actual
    mes_inicio = page.locator('select[id*="MesInicio"], select[id*="mesInicio"], select[id*="ddlMesInicio"]').first
    if await mes_inicio.is_visible():
        month_map = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        month_label = f"{month_map[now.month]} {now.year}"
        try:
            await mes_inicio.select_option(label=month_label)
        except Exception:
            # Intentar solo con el mes
            await mes_inicio.select_option(label=month_map[now.month])
        print(f"[OK] Mes Inicio: {month_label}")

    # Configurar Mes Final = mes actual
    mes_final = page.locator('select[id*="MesFinal"], select[id*="mesFinal"], select[id*="ddlMesFinal"]').first
    if await mes_final.is_visible():
        try:
            await mes_final.select_option(label=month_label)
        except Exception:
            await mes_final.select_option(label=month_map[now.month])
        print(f"[OK] Mes Final: {month_label}")

    # Ingresar email
    email_input = page.locator('input[id*="Email"], input[id*="email"], input[type="email"], input[id*="txtEmail"]').first
    if await email_input.is_visible():
        await email_input.fill(REPORT_EMAIL)
        print(f"[OK] Email ingresado: {REPORT_EMAIL}")

    # Marcar checkbox "Seleccione Departamentos" (marcar todos)
    dept_checkbox = page.locator('input[type="checkbox"][id*="Todos"], input[type="checkbox"][id*="todos"], input[type="checkbox"][id*="SelectAll"]').first
    if await dept_checkbox.is_visible():
        await dept_checkbox.check()
        print("[OK] Todos los departamentos seleccionados.")
    else:
        # Intentar con el checkbox visible en la lista
        checkboxes = page.locator('input[type="checkbox"]')
        count = await checkboxes.count()
        for i in range(count):
            cb = checkboxes.nth(i)
            if await cb.is_visible():
                await cb.check()
        print("[OK] Departamentos seleccionados.")

    # Click en "DESCARGAR"
    descargar_btn = page.locator('input[value="DESCARGAR"], button:has-text("DESCARGAR"), input[id*="btnDescargar"]').first
    await descargar_btn.click()
    print("[OK] Solicitud de descarga enviada. El reporte será enviado al email.")

    # Esperar confirmación
    await page.wait_for_timeout(5000)


async def main():
    """Función principal de automatización."""
    if not COPEC_RUT or not COPEC_PASSWORD:
        print("[ERROR] Credenciales no configuradas. Configura COPEC_RUT y COPEC_PASSWORD.")
        sys.exit(1)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            await login(page)
            await navigate_to_download(page)
            await configure_and_download(page)
            print("\n[DONE] Proceso completado. Espera ~5 minutos para recibir el correo.")
        except Exception as e:
            print(f"[ERROR] {e}")
            # Capturar screenshot para debug
            await page.screenshot(path="data/error_screenshot.png")
            print("[DEBUG] Screenshot guardado en data/error_screenshot.png")
            sys.exit(1)
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
