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


def search_copec_email(mail, max_retries=15, wait_seconds=60):
    """
    Busca el correo de Copec con el reporte adjunto.
    Optimizado: usa IMAP SEARCH por remitente/asunto antes de descargar emails completos.
    Reintenta varias veces esperando a que llegue el correo.
    """
    mail.select("INBOX")

    for attempt in range(1, max_retries + 1):
        print(f"\n[INFO] Intento {attempt}/{max_retries} - Buscando correo de Copec...")

        # Buscar correos recientes (últimos 3 días para más margen)
        date_since = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")

        # Estrategia 1: Buscar por remitente conocido de Copec
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

        # Estrategia 2: Buscar por asunto
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
            print(f"[WAIT] No se encontraron correos candidatos de Copec. Esperando {wait_seconds}s...")
            time.sleep(wait_seconds)
            continue

        print(f"[INFO] {len(candidate_ids)} email(s) candidato(s) encontrados. Revisando adjuntos...")

        # Solo descargar los emails candidatos (no todos los 100+)
        # Revisar del más reciente al más antiguo
        sorted_ids = sorted(candidate_ids, key=lambda x: int(x), reverse=True)

        for msg_id in sorted_ids:
            try:
                # Primero obtener solo headers para verificar
                _, header_data = mail.fetch(msg_id, "(BODY[HEADER.FIELDS (FROM SUBJECT CONTENT-TYPE)])")
                header_text = header_data[0][1].decode("utf-8", errors="replace").lower()

                is_copec = any(kw in header_text for kw in COPEC_SENDERS)
                has_subject = any(kw in header_text for kw in COPEC_SUBJECTS)

                if not (is_copec or has_subject):
                    continue

                # Verificar si tiene adjunto mirando BODYSTRUCTURE (más rápido que descargar todo)
                _, struct_data = mail.fetch(msg_id, "(BODYSTRUCTURE)")
                struct_text = struct_data[0][1].decode("utf-8", errors="replace").lower() if isinstance(struct_data[0][1], bytes) else str(struct_data[0]).lower()

                has_attachment = "xlsx" in struct_text or "xls" in struct_text or "csv" in struct_text or "spreadsheet" in struct_text or "octet-stream" in struct_text

                if not has_attachment:
                    # Decodificar subject para log
                    print(f"  [SKIP] Email candidato sin adjunto Excel (id={msg_id.decode()})")
                    continue

                # Solo ahora descargar el email completo
                print(f"  [FETCH] Descargando email completo (id={msg_id.decode()})...")
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Verificar adjuntos Excel
                for part in msg.walk():
                    fname = part.get_filename()
                    if fname and any(fname.lower().endswith(ext) for ext in (".xlsx", ".xls", ".csv")):
                        from_header = msg.get("From", "")
                        subject_header = msg.get("Subject", "")
                        decoded_subject = decode_header_str(subject_header)
                        print(f"[OK] Correo de Copec con Excel encontrado: '{decoded_subject}' de {from_header}")
                        return msg

                print(f"  [SKIP] Email descargado pero sin adjuntos Excel válidos (id={msg_id.decode()})")

            except Exception as e:
                print(f"  [WARN] Error procesando email id={msg_id.decode()}: {e}")
                continue

        print(f"[WAIT] Correo de Copec con Excel no encontrado aún. Esperando {wait_seconds}s...")
        time.sleep(wait_seconds)

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


def download_attachment(msg):
    """Descarga el archivo Excel adjunto del correo."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    downloaded_files = []

    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue

        filename = part.get_filename()
        if filename:
            decoded_name = decode_header_str(filename)

            # Solo descargar archivos Excel
            if decoded_name.lower().endswith((".xlsx", ".xls", ".csv")):
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

    mail = connect_imap()

    try:
        msg = search_copec_email(mail)
        if msg:
            files = download_attachment(msg)
            if files:
                print(f"\n[DONE] {len(files)} archivo(s) descargado(s) en '{OUTPUT_DIR}/'")
                # Escribir el path del archivo principal para uso en pipeline
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
