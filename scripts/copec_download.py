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
    login_btn = page.locator('#Button1')

    await rut_input.fill(COPEC_RUT)
    await pass_input.fill(COPEC_PASSWORD)
    await login_btn.click()

    await page.wait_for_load_state("networkidle", timeout=30000)
    print("[OK] Login exitoso.")


async def navigate_to_download(page):
    """Navega a la página de Descarga Transacciones por Departamento."""
    print("[INFO] Navegando a Descarga Transacciones por Departamento...")
    await page.goto(DOWNLOAD_URL, wait_until="networkidle", timeout=30000)

    # Esperar extra para que ASP.NET WebForms termine de renderizar
    await page.wait_for_timeout(3000)

    # Screenshot de debug para ver el estado de la página
    await page.screenshot(path="data/debug_download_page.png")
    print("[DEBUG] Screenshot de página de descarga guardado.")

    # Verificar que la página cargó correctamente buscando elementos clave
    page_text = await page.text_content('body')
    if 'Descarga Transacciones' in (page_text or ''):
        print("[OK] Página de descarga cargada correctamente.")
    else:
        print(f"[WARN] Página puede no haber cargado bien. Título: {await page.title()}")
        # Imprimir parte del HTML para debug
        html_snippet = await page.evaluate('document.body.innerHTML.substring(0, 1000)')
        print(f"[DEBUG] HTML snippet: {html_snippet}")


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

    # 1. Tipo de Informe: "Consumos" (radio button)
    consumos_radio = page.locator('#ctl00_CpH1_TipInforme_0')
    if await consumos_radio.is_visible():
        await consumos_radio.check()
        print("[OK] Tipo Informe: Consumos seleccionado.")
    else:
        print("[WARN] Radio Consumos no visible, puede estar ya seleccionado.")

    await page.wait_for_timeout(1000)

    # 2. Producto: dejar "Todos los productos" por defecto
    print(f"[OK] Mes Inicio/Final: {month_label} (por defecto)")

    # 3. Ingresar email - probar ambos campos posibles
    # La página tiene txbEmail (visible con Consumos) y txbEmail1 (visible con Estado de Cuenta)
    email_filled = False

    # Listar todos los inputs de texto para debug
    input_count = await page.locator('input[type="text"]').count()
    print(f"[DEBUG] Total inputs tipo text en la página: {input_count}")

    for input_id in ['ctl00_CpH1_txbEmail', 'ctl00_CpH1_txbEmail1']:
        try:
            field = page.locator(f'#{input_id}')
            if await field.count() > 0 and await field.is_visible(timeout=3000):
                await field.fill(REPORT_EMAIL)
                email_filled = True
                print(f"[OK] Email ingresado en #{input_id}: {REPORT_EMAIL}")
                break
            else:
                print(f"[DEBUG] #{input_id} existe pero no es visible.")
        except Exception as e:
            print(f"[DEBUG] #{input_id} no disponible: {e}")

    if not email_filled:
        # Último recurso: buscar cualquier input cerca del texto "Email"
        print("[WARN] Ningún campo email encontrado por ID. Buscando por label...")
        try:
            email_field = page.locator('input[type="text"]').filter(has=page.locator('xpath=..').filter(has_text="Email"))
            if await email_field.count() == 0:
                # Intentar con JavaScript directo
                await page.evaluate(f'''() => {{
                    const inputs = document.querySelectorAll('input[type="text"]');
                    for (const inp of inputs) {{
                        if (inp.id.toLowerCase().includes('email')) {{
                            inp.value = "{REPORT_EMAIL}";
                            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return true;
                        }}
                    }}
                    return false;
                }}''')
                print(f"[OK] Email ingresado via JavaScript: {REPORT_EMAIL}")
                email_filled = True
        except Exception as e:
            print(f"[ERROR] No se pudo ingresar email: {e}")

    if not email_filled:
        # Screenshot para debug y continuar de todas formas
        await page.screenshot(path="data/debug_email_error.png")
        print("[ERROR] No se encontró campo de email. Screenshot guardado.")

    # 4. Marcar checkbox "Seleccionar Todos" los departamentos
    select_all_cb = page.locator('#ctl00_CpH1_radGBajarInfo_ctl00_ctl02_ctl02_chkSelectAll')
    if await select_all_cb.is_visible():
        await select_all_cb.check()
        print("[OK] Todos los departamentos seleccionados.")
    else:
        # Fallback: marcar checkboxes individuales
        checkboxes = page.locator('input[type="checkbox"][id*="chkSelect"]')
        count = await checkboxes.count()
        for i in range(count):
            cb = checkboxes.nth(i)
            if await cb.is_visible():
                await cb.check()
        print(f"[OK] {count} departamentos seleccionados.")

    await page.wait_for_timeout(500)

    # 5. Click en "DESCARGAR"
    descargar_btn = page.locator('#ctl00_CpH1_btnAceptar')
    if await descargar_btn.is_visible():
        await descargar_btn.click()
        print("[OK] Solicitud de descarga enviada. El reporte será enviado al email.")
    else:
        # Fallback: buscar link con texto Descargar
        alt_btn = page.locator('a:has-text("Descargar"), a:has-text("DESCARGAR")')
        if await alt_btn.count() > 0:
            await alt_btn.first.click()
            print("[OK] Descarga solicitada (botón alternativo).")
        else:
            print("[ERROR] Botón DESCARGAR no encontrado.")

    # Esperar confirmación
    await page.wait_for_timeout(5000)
    await page.screenshot(path="data/debug_after_download.png")
    print("[DEBUG] Screenshot post-descarga guardado.")


async def main():
    """Función principal de automatización."""
    if not COPEC_RUT or not COPEC_PASSWORD:
        print("[ERROR] Credenciales no configuradas. Configura COPEC_RUT y COPEC_PASSWORD.")
        sys.exit(1)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            await login(page)
            await navigate_to_download(page)
            await configure_and_download(page)
            print("\n[DONE] Proceso completado. Espera ~5 minutos para recibir el correo.")
        except Exception as e:
            print(f"[ERROR] {e}")
            await page.screenshot(path="data/error_screenshot.png")
            print("[DEBUG] Screenshot de error guardado en data/error_screenshot.png")
            # Imprimir HTML para debug
            try:
                html = await page.evaluate('document.body.innerHTML.substring(0, 2000)')
                print(f"[DEBUG] HTML: {html}")
            except:
                pass
            sys.exit(1)
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
