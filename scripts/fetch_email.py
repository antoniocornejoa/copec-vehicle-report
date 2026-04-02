"""
Recupera el archivo Excel de transacciones Copec desde el correo electrónico vía IMAP.
Busca el correo más reciente de Copec con adjunto Excel y lo descarga.
"""

import imaplib
import email
import os
import sys
import time
from email.header import decode_header
from datetime import datetime, timedelta

# Configuración desde variables de entorno (GitHub Secrets)
IMAP_SERVER = os.environ.get("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
EMAIL_USER = os.environ.get("EMAIL_USER", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")  # App password para Gmail
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "data")

# Palabras clave para identificar el correo de Copec
# Nota: NO incluir "noreply" solo, ya que matchea con noreply@google.com etc.
COPEC_SENDERS = ["copec", "cuponelectronico"]
COPEC_SUBJECTS = ["transacciones", "descarga", "copec", "cupon"]


def connect_imap():
    """Conecta al servidor IMAP."""
    print(f"[INFO] Conectando a {IMAP_SERVER}:{IMAP_PORT}...")
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(EMAIL_USER, EMAIL_PASSWORD)
    print("[OK] Conexión IMAP establecida.")
    return mail


def search_copec_email(mail, max_retries=10, wait_seconds=60):
    """
    Busca el correo de Copec con el reporte adjunto.
    Reintenta varias veces esperando a que llegue el correo.
    """
    mail.select("INBOX")

    for attempt in range(1, max_retries + 1):
        print(f"[INFO] Intento {attempt}/{max_retries} - Buscando correo de Copec...")

        # Buscar correos recientes (últimas 24 horas)
        date_since = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
        _, message_ids = mail.search(None, f'(SINCE "{date_since}")')

        if not message_ids[0]:
            print(f"[WAIT] No se encontraron correos recientes. Esperando {wait_seconds}s...")
            time.sleep(wait_seconds)
            continue

        ids = message_ids[0].split()
        # Revisar del más reciente al más antiguo
        for msg_id in reversed(ids):
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Decodificar remitente
            from_header = msg.get("From", "").lower()
            subject_header = msg.get("Subject", "")
            decoded_subject = ""
            for part, encoding in decode_header(subject_header):
                if isinstance(part, bytes):
                    decoded_subject += part.decode(encoding or "utf-8", errors="replace")
                else:
                    decoded_subject += part
            decoded_subject_lower = decoded_subject.lower()

            # Verificar si es de Copec (remitente O asunto debe contener "copec")
            is_copec_sender = any(kw in from_header for kw in COPEC_SENDERS)
            has_copec_subject = any(kw in decoded_subject_lower for kw in COPEC_SUBJECTS)

            # Verificar si tiene adjunto Excel
            has_excel = False
            for part in msg.walk():
                fname = part.get_filename()
                if fname and any(fname.lower().endswith(ext) for ext in (".xlsx", ".xls", ".csv")):
                    has_excel = True
                    break

            if (is_copec_sender or has_copec_subject) and has_excel:
                print(f"[OK] Correo de Copec con Excel encontrado: '{decoded_subject}' de {from_header}")
                return msg
            elif is_copec_sender or has_copec_subject:
                print(f"[DEBUG] Correo de Copec sin Excel: '{decoded_subject}' de {from_header}")

        print(f"[WAIT] Correo de Copec con Excel no encontrado aún. Esperando {wait_seconds}s...")
        time.sleep(wait_seconds)

    print("[ERROR] No se encontró el correo de Copec después de todos los reintentos.")
    return None


def download_attachment(msg):
    """Descarga el archivo Excel adjunto del correo."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    downloaded_files = []

    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue

        filename = part.get_filename()
        if filename:
            # Decodificar nombre de archivo
            decoded_name = ""
            for name_part, encoding in decode_header(filename):
                if isinstance(name_part, bytes):
                    decoded_name += name_part.decode(encoding or "utf-8", errors="replace")
                else:
                    decoded_name += name_part

            # Solo descargar archivos Excel
            if decoded_name.lower().endswith((".xlsx", ".xls", ".csv")):
                filepath = os.path.join(OUTPUT_DIR, decoded_name)
                with open(filepath, "wb") as f:
                    f.write(part.get_payload(decode=True))
                print(f"[OK] Archivo descargado: {filepath}")
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
