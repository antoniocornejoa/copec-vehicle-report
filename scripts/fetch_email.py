"""
Recupera el archivo Excel de transacciones Copec desde el correo electrónico vía IMAP.
Busca el correo más reciente de Copec con adjunto Excel y lo descarga.

Optimizado: busca primero por headers (FROM/SUBJECT) vía IMAP SEARCH,
luego solo descarga los emails candidatos completos.
"""

import imaplib
import email
import os
import sys
import time
from email.header import decode_header
from datetime import datetime, timedelta

# Forzar flush en cada print para que GitHub Actions muestre logs en tiempo real
import functools
print = functools.partial(print, flush=True)

# Configuración desde variables de entorno (GitHub Secrets)
IMAP_SERVER = os.environ.get("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
EMAIL_USER = os.environ.get("EMAIL_USER", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")  # App password para Gmail
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "data")

# Palabras clave para identificar el correo de Copec
COPEC_SENDERS = ["copec", "cuponelectronico"]
COPEC_SUBJECTS = ["transacciones", "descarga", "copec", "cupon"]


def connect_imap():
    """Conecta al servidor IMAP con timeout."""
    print(f"[INFO] Conectando a {IMAP_SERVER}:{IMAP_PORT}...")
    # Timeout de 30 segundos para evitar cuelgues
    imaplib.IMAP4_SSL.timeout = 30
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(EMAIL_USER, EMAIL_PASSWORD)
    print("[OK] Conexión IMAP establecida.")
    return mail


def search_copec_emails(mail, fetch_all=False, max_retries=15, wait_seconds=60):
    """
    Busca correos de Copec con reportes adjuntos.
    Si fetch_all=True, retorna TODOS los correos con adjuntos (para acumular historial).
    Si fetch_all=False, retorna solo el más reciente (comportamiento original).
    """
    mail.select("INBOX")

    # Si buscamos todo el historial, buscar desde enero 2026
    if fetch_all:
        date_since = "01-Jan-2026"
        max_retries = 1  # No reintentar en modo histórico
        print("[INFO] Modo histórico: buscando TODOS los correos de Copec desde Enero 2026...")
    else:
        date_since = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")

    found_messages = []

    for attempt in range(1, max_retries + 1):
        if not fetch_all:
            print(f"\n[INFO] Intento {attempt}/{max_retries} - Buscando correo de Copec...")

        candidate_ids = set()
        for sender_kw in COPEC_SENDERS:
            try:
                _, ids = mail.search(None, f'(SINCE "{date_since}" FROM "{sender_kw}")')
                if ids[0]:
                    for mid in ids[0].split():
                        candidate_ids.add(mid)
                    print(f"  [SEARCH] FROM '{sender_kw}': {len(ids[0].split())} resultado(s)")
            except Exception as e:
                print(f"  [WARN] Error buscando FROM '{sender_kw}': {e}")

        for subject_kw in COPEC_SUBJECTS:
            try:
                _, ids = mail.search(None, f'(SINCE "{date_since}" SUBJECT "{subject_kw}")')
                if ids[0]:
                    for mid in ids[0].split():
                        candidate_ids.add(mid)
                    print(f"  [SEARCH] SUBJECT '{subject_kw}': {len(ids[0].split())} resultado(s)")
            except Exception as e:
                print(f"  [WARN] Error buscando SUBJECT '{subject_kw}': {e}")

        if not candidate_ids:
            if not fetch_all:
                print(f"[WAIT] No se encontraron correos candidatos de Copec. Esperando {wait_seconds}s...")
                time.sleep(wait_seconds)
            continue

        print(f"[INFO] {len(candidate_ids)} email(s) candidato(s) encontrados. Revisando adjuntos...")

        # Revisar del más reciente al más antiguo
        sorted_ids = sorted(candidate_ids, key=lambda x: int(x), reverse=True)

        # En modo historial, solo tomar 1 por mes (el más reciente de cada mes tiene datos completos)
        seen_subjects = set()

        for msg_id in sorted_ids:
            try:
                _, header_data = mail.fetch(msg_id, "(BODY[HEADER.FIELDS (FROM SUBJECT DATE)])")
                header_text = header_data[0][1].decode("utf-8", errors="replace")
                header_lower = header_text.lower()

                is_copec = any(kw in header_lower for kw in COPEC_SENDERS)
                if not is_copec:
                    continue

                # Extraer subject para deduplicar por mes
                subject_line = ""
                for line in header_text.split("\r\n"):
                    if line.lower().startswith("subject:"):
                        subject_line = line[8:].strip()
                        break

                # En modo histórico, solo 1 email por periodo (ej: "Consumos Periodo May/2026")
                if fetch_all and subject_line in seen_subjects:
                    continue

                # Verificar adjunto
                _, struct_data = mail.fetch(msg_id, "(BODYSTRUCTURE)")
                struct_text = struct_data[0][1].decode("utf-8", errors="replace").lower() if isinstance(struct_data[0][1], bytes) else str(struct_data[0]).lower()

                has_attachment = any(kw in struct_text for kw in ["xlsx", "xls", "csv", "spreadsheet", "octet-stream"])

                if not has_attachment:
                    continue

                # Descargar email completo
                print(f"  [FETCH] Descargando: {subject_line} (id={msg_id.decode()})...")
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Verificar adjuntos Excel
                has_excel = False
                for part in msg.walk():
                    fname = part.get_filename()
                    if fname and any(fname.lower().endswith(ext) for ext in (".xlsx", ".xls", ".csv")):
                        has_excel = True
                        break

                if has_excel:
                    seen_subjects.add(subject_line)
                    print(f"  [OK] {subject_line}")

                    if fetch_all:
                        found_messages.append(msg)
                    else:
                        return msg  # Modo normal: retornar el primero encontrado

            except Exception as e:
                print(f"  [WARN] Error procesando email id={msg_id.decode()}: {e}")
                continue

        if fetch_all and found_messages:
            print(f"\n[OK] {len(found_messages)} correo(s) con datos Copec encontrados")
            return found_messages

        if not fetch_all:
            print(f"[WAIT] Correo de Copec con Excel no encontrado aún. Esperando {wait_seconds}s...")
            time.sleep(wait_seconds)

    if fetch_all:
        return found_messages  # Puede ser lista vacía
    print("[ERROR] No se encontró el correo de Copec después de todos los reintentos.")
    return None


def decode_header_str(header_value):
    """Decodifica un header de email a string legible."""
    decoded = ""
    for part, encoding in decode_header(header_value):
        if isinstance(part, bytes):
            decoded += part.decode(encoding or "utf-8", errors="replace")
        else:
            decoded += part
    return decoded


def download_attachment(msg, suffix=""):
    """Descarga el archivo Excel adjunto del correo."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    downloaded_files = []

    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue

        filename = part.get_filename()
        if filename:
            decoded_name = decode_header_str(filename)

            if decoded_name.lower().endswith((".xlsx", ".xls", ".csv")):
                # Si hay suffix (para modo histórico), agregar al nombre
                if suffix:
                    base, ext = os.path.splitext(decoded_name)
                    decoded_name = f"{base}_{suffix}{ext}"
                filepath = os.path.join(OUTPUT_DIR, decoded_name)
                with open(filepath, "wb") as f:
                    f.write(part.get_payload(decode=True))
                print(f"[OK] Archivo descargado: {filepath} ({os.path.getsize(filepath)} bytes)")
                downloaded_files.append(filepath)

    return downloaded_files


def main():
    """Función principal de recuperación de email."""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("[ERROR] Credenciales de email no configuradas.")
        print("  Configura EMAIL_USER y EMAIL_PASSWORD como variables de entorno.")
        sys.exit(1)

    # Modo histórico: descargar todos los correos de Copec
    fetch_all = os.environ.get("FETCH_ALL_MONTHS", "false").lower() == "true"

    mail = connect_imap()

    try:
        if fetch_all:
            messages = search_copec_emails(mail, fetch_all=True)
            if messages:
                all_files = []
                for i, msg in enumerate(messages):
                    subject = decode_header_str(msg.get("Subject", f"unknown_{i}"))
                    # Extraer periodo del subject (ej: "Consumos Periodo Abr/2026" -> "Abr_2026")
                    suffix = ""
                    if "Periodo" in subject:
                        period = subject.split("Periodo")[-1].strip().replace("/", "_").replace(" ", "")
                        suffix = period
                    else:
                        suffix = f"msg_{i}"
                    files = download_attachment(msg, suffix=suffix)
                    all_files.extend(files)
                if all_files:
                    print(f"\n[DONE] {len(all_files)} archivo(s) descargado(s) en '{OUTPUT_DIR}/'")
                    with open(os.path.join(OUTPUT_DIR, "latest_file.txt"), "w") as f:
                        f.write(all_files[0])
                    return all_files[0]
            else:
                print("[WARN] No se encontraron correos históricos de Copec.")
                sys.exit(1)
        else:
            msg = search_copec_emails(mail, fetch_all=False)
            if msg:
                files = download_attachment(msg)
                if files:
                    print(f"\n[DONE] {len(files)} archivo(s) descargado(s) en '{OUTPUT_DIR}/'")
                    with open(os.path.join(OUTPUT_DIR, "latest_file.txt"), "w") as f:
                        f.write(files[0])
                    return files[0]
                else:
                    print("[ERROR] El correo no contenía archivos Excel adjuntos.")
                    sys.exit(1)
            else:
                sys.exit(1)
    finally:
        mail.logout()


if __name__ == "__main__":
    main()
