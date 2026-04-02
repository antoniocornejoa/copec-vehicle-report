"""
Automatización de descarga de transacciones desde Cupón Electrónico Copec.
Usa Playwright para navegar el sitio, solicitar el reporte y enviarlo por email.
Navega a través del menú (Informes > Descarga Transacciones) en vez de URL directa.
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

    rut_input = page.locator('#TxbRutSA')
    pass_input = page.locator('#TxbClaveSA')
    login_btn = page.locator('#Button1')

    await rut_input.fill(COPEC_RUT)
    await pass_input.fill(COPEC_PASSWORD)

    # El click de login causa navegación - esperarla explícitamente
    async with page.expect_navigation(wait_until="networkidle", timeout=60000):
        await login_btn.click()

    # Esperar a que la página post-login termine de cargar completamente
    await page.wait_for_timeout(3000)
    await page.wait_for_load_state("domcontentloaded", timeout=30000)

    try:
        title = await page.title()
        url = page.url
        print(f"[OK] Login exitoso. Título: {title}, URL: {url}")
    except:
        print("[OK] Login completado (página aún cargando).")

    await page.screenshot(path="data/debug_after_login.png")


async def navigate_to_download(page):
    """Navega a Descarga Transacciones via menú o URL directa."""

    # Estrategia 1: Intentar navegar por menú
    print("[INFO] Intentando navegar via menú: Informes > Descarga Transacciones...")
    try:
        informes_menu = page.locator('a:has-text("Informes"), li:has-text("Informes") > a').first
        if await informes_menu.count() > 0 and await informes_menu.is_visible(timeout=5000):
            await informes_menu.hover()
            await page.wait_for_timeout(1500)

            # Buscar submenú
            selectors = [
                'a:has-text("Descarga Transacciones")',
                'a:has-text("Bajar Info")',
                'a[href*="cteBajarInfo"]',
                'a[href*="BajarInfo"]',
            ]

            for sel in selectors:
                loc = page.locator(sel)
                if await loc.count() > 0:
                    print(f"[DEBUG] Link encontrado: {sel}")
                    async with page.expect_navigation(wait_until="networkidle", timeout=30000):
                        await loc.first.click()
                    await page.wait_for_timeout(3000)

                    # Verificar que cargó
                    page_text = await page.text_content('body') or ''
                    if 'Ingrese Email' in page_text or 'DESCARGAR' in page_text or 'Descarga Transacciones' in page_text:
                        print("[OK] Página de descarga cargada via menú.")
                        await page.screenshot(path="data/debug_download_page.png")
                        return
                    else:
                        print("[WARN] Menú clickeado pero página no es la correcta.")
                    break

            # Si llegamos aquí, el menú no funcionó. Debug info:
            await page.screenshot(path="data/debug_menu_informes.png")
            print("[WARN] Navegación por menú no funcionó.")
        else:
            print("[WARN] Menú Informes no encontrado.")
    except Exception as e:
        print(f"[WARN] Error en navegación por menú: {e}")

    # Estrategia 2: Navegar directamente a la URL
    print("[INFO] Intentando navegación directa a URL de descarga...")
    DOWNLOAD_URL = "https://cuponelectronico.copec.cl/VistasCte/cteBajarInfo.aspx"

    for attempt in range(1, 4):
        try:
            await page.goto(DOWNLOAD_URL, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            page_text = await page.text_content('body') or ''
            if 'Ingrese Email' in page_text or 'DESCARGAR' in page_text or 'Descarga Transacciones' in page_text:
                print(f"[OK] Página de descarga cargada via URL directa (intento {attempt}).")
                await page.screenshot(path="data/debug_download_page.png")
                return
            else:
                title = await page.title()
                print(f"[WARN] Intento {attempt}: Página no es la correcta. Título: {title}")
        except Exception as e:
            print(f"[WARN] Intento {attempt} URL directa falló: {e}")

        if attempt < 3:
            await page.wait_for_timeout(3000)

    # Si nada funcionó, listar links para debug y fallar
    await page.screenshot(path="data/debug_navigation_failed.png")
    all_links = await page.evaluate('''() => {
        return Array.from(document.querySelectorAll('a')).map(a => ({
            text: a.textContent.trim().substring(0, 60),
            href: a.href
        })).filter(a => a.text.length > 0).slice(0, 30);
    }''')
    print(f"[DEBUG] Links disponibles:")
    for link in all_links:
        print(f"  - '{link['text']}' -> {link['href']}")
    raise Exception("No se pudo navegar a la página de descarga por ningún método.")

    await download_link.click()
    await page.wait_for_load_state("networkidle", timeout=30000)
    await page.wait_for_timeout(3000)

    # Verificar que estamos en la página correcta
    page_text = await page.text_content('body') or ''
    title = await page.title()

    if 'Descarga Transacciones' in page_text or 'Ingrese Email' in page_text or 'DESCARGAR' in page_text:
        print("[OK] Página de descarga cargada correctamente.")
    else:
        await page.screenshot(path="data/debug_wrong_page.png")
        print(f"[WARN] Página puede no haber cargado bien. Título: {title}")
        # Imprimir snippet del HTML
        snippet = await page.evaluate('document.body.innerText.substring(0, 500)')
        print(f"[DEBUG] Contenido: {snippet}")

    await page.screenshot(path="data/debug_download_page.png")


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
    if await consumos_radio.count() > 0:
        try:
            await consumos_radio.check(timeout=5000)
            print("[OK] Tipo Informe: Consumos")
        except:
            print("[WARN] No se pudo marcar radio Consumos, puede estar ya seleccionado.")
    else:
        print("[WARN] Radio Consumos no encontrado.")

    await page.wait_for_timeout(1000)
    print(f"[OK] Mes Inicio/Final: {month_label} (por defecto)")

    # 2. Ingresar email - probar ambos campos
    email_filled = False
    for input_id in ['ctl00_CpH1_txbEmail', 'ctl00_CpH1_txbEmail1']:
        try:
            field = page.locator(f'#{input_id}')
            if await field.count() > 0 and await field.is_visible(timeout=3000):
                await field.fill(REPORT_EMAIL)
                email_filled = True
                print(f"[OK] Email ingresado en #{input_id}: {REPORT_EMAIL}")
                break
        except:
            continue

    if not email_filled:
        # JavaScript fallback
        result = await page.evaluate(f'''() => {{
            const inputs = document.querySelectorAll('input[type="text"]');
            for (const inp of inputs) {{
                if (inp.id.toLowerCase().includes('email')) {{
                    inp.value = "{REPORT_EMAIL}";
                    inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    return inp.id;
                }}
            }}
            return null;
        }}''')
        if result:
            print(f"[OK] Email ingresado via JavaScript en #{result}: {REPORT_EMAIL}")
            email_filled = True
        else:
            await page.screenshot(path="data/debug_no_email_field.png")
            raise Exception("No se encontró ningún campo de email en la página")

    # 3. Marcar departamentos
    select_all_cb = page.locator('#ctl00_CpH1_radGBajarInfo_ctl00_ctl02_ctl02_chkSelectAll')
    if await select_all_cb.count() > 0 and await select_all_cb.is_visible(timeout=3000):
        await select_all_cb.check()
        print("[OK] Todos los departamentos seleccionados.")
    else:
        # Marcar checkboxes individuales
        checkboxes = page.locator('input[type="checkbox"][id*="chkSelect"]')
        count = await checkboxes.count()
        if count > 0:
            for i in range(count):
                cb = checkboxes.nth(i)
                if await cb.is_visible():
                    await cb.check()
            print(f"[OK] {count} departamentos seleccionados.")
        else:
            print("[WARN] No se encontraron checkboxes de departamentos.")

    await page.wait_for_timeout(500)

    # 4. Click en DESCARGAR
    descargar_clicked = False
    descargar_btn = page.locator('#ctl00_CpH1_btnAceptar')
    if await descargar_btn.count() > 0 and await descargar_btn.is_visible(timeout=3000):
        await descargar_btn.click()
        descargar_clicked = True
        print("[OK] Botón DESCARGAR clickeado.")
    else:
        # Fallback: buscar por texto
        alt_btn = page.locator('a:has-text("Descargar"), a:has-text("DESCARGAR")')
        if await alt_btn.count() > 0:
            await alt_btn.first.click()
            descargar_clicked = True
            print("[OK] Descarga solicitada (botón alternativo).")

    if not descargar_clicked:
        await page.screenshot(path="data/debug_no_descargar.png")
        raise Exception("Botón DESCARGAR no encontrado. La descarga NO se ejecutó.")

    # Esperar que procese la solicitud
    await page.wait_for_timeout(5000)
    await page.screenshot(path="data/debug_after_download.png")
    print("[DEBUG] Screenshot post-descarga guardado.")
    print("[OK] Solicitud de descarga enviada. El reporte será enviado al email.")


async def main():
    """Función principal de automatización."""
    if not COPEC_RUT or not COPEC_PASSWORD:
        print("[ERROR] Credenciales no configuradas.")
        sys.exit(1)

    os.makedirs("data", exist_ok=True)

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
            print("\n[DONE] Proceso completado exitosamente.")
        except Exception as e:
            print(f"\n[ERROR] {e}")
            try:
                await page.screenshot(path="data/error_screenshot.png")
                print("[DEBUG] Screenshot de error guardado.")
                html = await page.evaluate('document.body.innerText.substring(0, 1000)')
                print(f"[DEBUG] Contenido página: {html}")
            except:
                pass
            sys.exit(1)
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
