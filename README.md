# Reporte Automatico de Rendimiento Vehicular

Genera reportes mensuales de consumo de combustible a partir de los datos de **Cupon Electronico COPEC**, publicados automaticamente en GitHub Pages.

## Flujo automatizado

```
Copec (Playwright) -> Email (IMAP) -> Excel -> Procesamiento (Python) -> HTML Dashboard -> GitHub Pages
```

1. **copec_download.py** - Se conecta a cuponelectronico.copec.cl, navega a Descarga de Transacciones y solicita el reporte por email
2. **fetch_email.py** - Recupera el Excel adjunto desde el correo electronico via IMAP
3. **process_data.py** - Procesa el Excel y genera un JSON estructurado con metricas por vehiculo
4. **generate_report.py** - Genera un dashboard HTML interactivo con graficos y tablas

## Configuracion inicial

### 1. Crear repositorio en GitHub

```bash
git init
git add .
git commit -m "Configuracion inicial reporte vehicular"
git remote add origin https://github.com/TU_USUARIO/copec-vehicle-report.git
git push -u origin main
```

### 2. Configurar GitHub Secrets

En tu repositorio: **Settings > Secrets and variables > Actions**, agrega:

| Secret | Descripcion | Ejemplo |
|--------|-------------|---------|
| `COPEC_RUT` | RUT de acceso a Cupon Electronico | `76734196-2` |
| `COPEC_PASSWORD` | Clave de acceso | `tu_clave` |
| `REPORT_EMAIL` | Email donde llega el reporte | `acornejo@cindependencia.cl` |
| `IMAP_SERVER` | Servidor IMAP del correo | `imap.gmail.com` |
| `IMAP_PORT` | Puerto IMAP (SSL) | `993` |
| `EMAIL_USER` | Usuario del correo | `acornejo@cindependencia.cl` |
| `EMAIL_PASSWORD` | Clave del correo (App Password para Gmail) | `xxxx xxxx xxxx xxxx` |

### 3. Habilitar GitHub Pages

En **Settings > Pages**: selecciona **GitHub Actions** como fuente.

### 4. Ejecucion

- **Automatica**: Se ejecuta el dia 2 de cada mes a las 9:00 AM (hora Chile)
- **Manual**: Desde la pestana **Actions** > **Reporte Mensual** > **Run workflow**
  - Puedes saltar la descarga de Copec si ya tienes el Excel en `data/`
  - Puedes saltar la recuperacion del email si ya descargaste el archivo

## Ejecucion local

```bash
# Instalar dependencias
pip install -r requirements.txt
playwright install chromium

# Colocar archivo Excel en data/
cp tu_archivo.xlsx data/

# Procesar y generar reporte
python scripts/process_data.py
python scripts/generate_report.py

# Abrir reporte
open docs/index.html
```

## Estructura del proyecto

```
copec-vehicle-report/
├── .github/
│   └── workflows/
│       └── monthly_report.yml    # GitHub Actions workflow
├── scripts/
│   ├── copec_download.py         # Automatizacion Copec con Playwright
│   ├── fetch_email.py            # Recuperacion de email via IMAP
│   ├── process_data.py           # Procesamiento de datos Excel
│   └── generate_report.py        # Generacion de reporte HTML
├── data/                         # Datos procesados (JSON)
├── docs/                         # Reporte HTML (GitHub Pages)
├── requirements.txt
├── .gitignore
└── README.md
```

## Nota sobre Gmail

Si usas Gmail, necesitas crear una **App Password**:
1. Ve a myaccount.google.com > Seguridad > Verificacion en 2 pasos (debe estar activada)
2. Busca "Contrasenas de aplicaciones"
3. Crea una nueva contrasena para "Correo" en "Otra (nombre personalizado)"
4. Usa esa contrasena de 16 caracteres como `EMAIL_PASSWORD`
