"""
Automatización de descarga de transacciones desde Cupón Electrónico Copec.
Usa Playwright para navegar el sitio, solicitar el reporte y enviarlo por email.
IDs de elementos obtenidos directamente de la página real de Copec.
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
DOWNLOAD_URL = "https://cuponelectronico.copec.cl/VistasCte/cteBajarInfo.aspx"


async def login(page):
    """Inicia sesión en Cupón Electrónico Copec."""
    print(f"[INFO] Navegando a {COPEC_URL}...")
    await page.goto(COPEC_URL, wait_until="networkidle", timeout=60000)

    # Campos de login con IDs exactos de la página Copec
    rut_input = page.locator('#TxbRutSA')
    pass_input = page.locator('#TxbClaveSA')
    login_btn = page.locator('#Button1')  # <a> link "INGRESAR"

    await rut_input.fill(COPEC_RUT)
    await pass_input.fill(COPEC_PASSWORD)
    await login_btn.click()

    # Esperar a que cargue la página principal
    await page.wait_for_load_state("networkidle", timeout=30000)
    print("[OK] Login exitoso.")


async def navigate_to_download(page):
    """Navega directamente a la página de Descarga Transacciones por Departamento."""
    print("[INFO] Navegando a Descarga Transacciones por Departamento...")

    # Navegar directamente a la URL de descarga (más confiable que hover en menú)
    await page.goto(DOWNLOAD_URL, wait_until="networkidle", timeout=30000)
    print("[OK] Página de descarga cargada.")


async def configure_and_download(page):
    """Configura los filtros y solicita la descarga."""
    now = datetime.now()
    month_map = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    month_label = f"{month_map[now.month]} {now.year}"
    print(f"[INFO] Configurando descarga para: {month_label}")

    # 1. Tipo de Informe: "Consumos" (radio button, generalmente ya seleccionado)
    consumos_radio = page.locator('#ctl00_CpH1_TipInforme_0')
    if await consumos_radio.is_visible():
        await consumos_radio.check()
        print("[OK] Tipo Informe: Consumos")

    # 2. Producto: Usar RadComboBox de Telerik
    # Los meses y producto son RadComboBox (Telerik), no <select> estándar
    # Por defecto ya viene "Todos los productos" y meses del mes actual
    # Si necesitamos cambiar producto a PD, hacemos click en el combo y seleccionamos
    producto_input = page.locator('#ctl00_CpH1_cbProducto_Input')
    if await producto_input.is_visible():
        # Click para abrir el dropdown
        await producto_input.click()
        await page.wait_for_timeout(500)
        # Buscar la opción PD en el dropdown desplegado
        pd_option = page.locator('.rcbList .rcbItem, .rcbList li').filter(has_text="PD")
        if await pd_option.count() > 0:
            await pd_option.first.click()
            await page.wait_for_timeout(500)
            print("[OK] Producto PD seleccionado.")
        else:
            print("[INFO] Usando producto por defecto (Todos los productos).")

    # 3. Mes Inicio y Mes Final - por defecto ya vienen con el mes actual
    # No es necesario cambiarlos si queremos el mes actual
    print(f"[OK] Mes Inicio/Final: {month_label} (por defecto)")

    # 4. Ingresar email
    email_input = page.locator('#ctl00_CpH1_txbEmail')
    await email_input.fill(REPORT_EMAIL)
    print(f"[OK] Email ingresado: {REPORT_EMAIL}")

    # 5. Marcar checkbox "Seleccionar Todos" los departamentos
    select_all_cb = page.locator('#ctl00_CpH1_radGBajarInfo_ctl00_ctl02_ctl02_chkSelectAll')
    if await select_all_cb.is_visible():
        await select_all_cb.check()
        print("[OK] Todos los departamentos seleccionados.")
    else:
        # Fallback: marcar todos los checkboxes individuales
        checkboxes = page.locator('input[type="checkbox"][id*="chkSelect"]')
        count = await checkboxes.count()
        for i in range(count):
            cb = checkboxes.nth(i)
            if await cb.is_visible():
                await cb.check()
        print(f"[OK] {count} departamentos seleccionados.")

    # 6. Click en "DESCARGAR" - es un <a> link con __doPostBack
    descargar_btn = page.locator('#ctl00_CpH1_btnAceptar')
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
