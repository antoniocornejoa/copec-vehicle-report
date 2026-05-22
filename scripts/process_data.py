"""
Procesa el archivo Excel de transacciones Copec y genera datos JSON
para el reporte de rendimiento de vehículos.

Columnas esperadas del archivo Copec (pueden variar en nombre exacto):
- Fecha / FECHA
- Patente / PATENTE / Placa
- Departamento / DEPARTAMENTO
- Estación / ESTACION / Est. Servicio
- Producto / PRODUCTO
- Litros / LITROS / Cantidad
- Monto / MONTO / Valor Neto
- Kilometraje / KM / KILOMETRAJE (opcional)
- Conductor / CONDUCTOR (opcional)
"""

import json
import os
import sys
import glob
from datetime import datetime

import pandas as pd
import numpy as np


def find_excel_file(data_dir="data"):
    """Encuentra el archivo Excel más reciente en el directorio de datos."""
    # Primero verificar si hay un archivo indicado
    latest_file = os.path.join(data_dir, "latest_file.txt")
    if os.path.exists(latest_file):
        with open(latest_file) as f:
            path = f.read().strip()
            if os.path.exists(path):
                return path

    # Buscar archivos Excel en el directorio (case-insensitive para .XLS/.xls)
    files = []
    if os.path.isdir(data_dir):
        for f in os.listdir(data_dir):
            if f.lower().endswith((".xlsx", ".xls", ".csv")):
                files.append(os.path.join(data_dir, f))

    if not files:
        print(f"[ERROR] No se encontraron archivos Excel en '{data_dir}/'")
        sys.exit(1)

    # Retornar el más reciente
    latest = max(files, key=os.path.getmtime)
    print(f"[INFO] Archivo encontrado: {latest}")
    return latest


def normalize_columns(df):
    """Normaliza los nombres de columnas del DataFrame."""
    column_mapping = {}
    for col in df.columns:
        col_upper = str(col).upper().strip()

        if any(k in col_upper for k in ["FECHA", "DATE"]):
            column_mapping[col] = "fecha"
        elif any(k in col_upper for k in ["PATENTE", "PLACA", "VEHICULO", "VEHICLE"]):
            column_mapping[col] = "patente"
        elif any(k in col_upper for k in ["DEPARTAMENTO", "DEPTO", "DEPT"]):
            column_mapping[col] = "departamento"
        elif any(k in col_upper for k in ["ESTACION", "ESTACIÓN", "EST."]):
            column_mapping[col] = "estacion"
        elif any(k in col_upper for k in ["PRODUCTO", "PROD"]):
            column_mapping[col] = "producto"
        elif any(k in col_upper for k in ["LITRO", "CANTIDAD", "LTS", "VOLUMEN", "VOL."]):
            column_mapping[col] = "litros"
        elif any(k in col_upper for k in ["MONTO", "VALOR", "NETO", "IMPORTE"]):
            column_mapping[col] = "monto"
        elif any(k in col_upper for k in ["KM", "KILOMETR", "ODOMETRO", "ODÓMETRO", "ODOMET"]):
            column_mapping[col] = "kilometraje"
        elif any(k in col_upper for k in ["CONDUCTOR", "CHOFER", "DRIVER"]):
            column_mapping[col] = "conductor"
        elif any(k in col_upper for k in ["RENDIMIENTO"]):
            column_mapping[col] = "rendimiento"
        elif any(k in col_upper for k in ["PRECIO UNIT", "PRECIO_UNIT"]):
            column_mapping[col] = "precio_unitario"
        elif any(k in col_upper for k in ["HORA", "TIME"]):
            column_mapping[col] = "hora"
        elif any(k in col_upper for k in ["TARJETA", "CARD"]):
            column_mapping[col] = "tarjeta"

    df = df.rename(columns=column_mapping)
    return df


def load_data(filepath):
    """Carga el archivo de datos."""
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".csv":
        # Intentar diferentes separadores
        for sep in [",", ";", "\t", "|"]:
            try:
                df = pd.read_csv(filepath, sep=sep, encoding="utf-8")
                if len(df.columns) > 2:
                    break
            except Exception:
                try:
                    df = pd.read_csv(filepath, sep=sep, encoding="latin-1")
                    if len(df.columns) > 2:
                        break
                except Exception:
                    continue
    else:
        # Intentar leer como Excel con diferentes engines
        # Copec a veces envía archivos .xlsx que son en realidad XLS antiguo o HTML
        df = None
        engines_to_try = [
            ("openpyxl", "xlsx moderno"),
            ("xlrd", "xls antiguo"),
            (None, "auto-detect"),
        ]

        for engine, desc in engines_to_try:
            try:
                kwargs = {"sheet_name": 0}
                if engine:
                    kwargs["engine"] = engine
                df = pd.read_excel(filepath, **kwargs)
                print(f"[OK] Archivo leído con engine: {desc}")
                break
            except Exception as e:
                print(f"[DEBUG] Engine {desc} falló: {e}")

        # Si ningún engine Excel funcionó, intentar como texto (TSV/CSV)
        # Copec envía archivos .xlsx que son en realidad texto delimitado por tabs
        if df is None:
            print("[INFO] Intentando leer como archivo de texto (TSV/CSV)...")
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                for sep in ["\t", ",", ";"]:
                    try:
                        # Copec puede tener líneas de encabezado antes de los datos
                        # Leer las primeras líneas para detectar dónde empiezan los datos
                        with open(filepath, "r", encoding=encoding) as f:
                            lines = f.readlines()

                        # Buscar la línea que tiene los encabezados de columnas
                        header_row = 0
                        for i, line in enumerate(lines[:10]):
                            if any(kw in line.upper() for kw in ["PATENTE", "RUT", "FECHA", "LITRO", "DEPTO", "DEPARTAMENTO"]):
                                header_row = i
                                break

                        df = pd.read_csv(filepath, sep=sep, encoding=encoding,
                                        skiprows=header_row, header=0)
                        if len(df.columns) > 3:
                            print(f"[OK] Archivo leído como texto ({encoding}, sep='{repr(sep)}', skiprows={header_row})")
                            print(f"[DEBUG] Columnas: {list(df.columns)}")
                            break
                        else:
                            df = None
                    except Exception:
                        df = None
                if df is not None:
                    break

        # Si aún no funcionó, intentar como HTML
        if df is None:
            try:
                dfs = pd.read_html(filepath, encoding="latin-1")
                if dfs:
                    df = dfs[0]
                    print("[OK] Archivo leído como HTML")
            except Exception as e:
                print(f"[DEBUG] HTML falló: {e}")

        if df is None:
            with open(filepath, "rb") as f:
                header = f.read(200)
            print(f"[DEBUG] Primeros bytes del archivo: {header}")
            print(f"[ERROR] No se pudo leer el archivo con ningún método.")
            sys.exit(1)

    print(f"[INFO] Datos cargados: {len(df)} filas, {len(df.columns)} columnas")
    print(f"[INFO] Columnas originales: {list(df.columns)}")

    df = normalize_columns(df)
    print(f"[INFO] Columnas normalizadas: {list(df.columns)}")

    return df


def process_vehicle_data(df):
    """Procesa datos de consumo por vehículo."""
    if "patente" not in df.columns:
        print("[WARN] Columna 'patente' no encontrada. Usando primera columna como identificador.")
        df = df.rename(columns={df.columns[0]: "patente"})

    # Limpiar datos numéricos (usando clean_number global para formato chileno)
    for col in ["litros", "monto", "kilometraje", "rendimiento", "precio_unitario"]:
        if col in df.columns:
            raw_vals = df[col].head(5).tolist()
            print(f"[DEBUG] {col} valores crudos: {raw_vals} (tipo: {df[col].dtype})")
            df[col] = df[col].apply(lambda v: clean_number(v) if not isinstance(v, (int, float, np.integer, np.floating)) else round(float(v), 2))
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            print(f"[DEBUG] {col} después de limpiar: {df[col].head(5).tolist()}")

    # Agrupar por vehículo (patente)
    vehicles = {}
    grouped = df.groupby("patente")

    for patente, group in grouped:
        patente_str = str(patente).strip()
        if not patente_str or patente_str == "nan":
            continue

        vehicle_data = {
            "patente": patente_str,
            "total_litros": round(float(group["litros"].sum()), 2) if "litros" in group.columns else 0,
            "total_monto": round(float(group["monto"].sum()), 0) if "monto" in group.columns else 0,
            "num_cargas": len(group),
            "promedio_litros_carga": round(float(group["litros"].mean()), 2) if "litros" in group.columns else 0,
            "promedio_monto_carga": round(float(group["monto"].mean()), 0) if "monto" in group.columns else 0,
            "precio_unitario_promedio": round(float(group["precio_unitario"].mean()), 1) if "precio_unitario" in group.columns and group["precio_unitario"].sum() > 0 else 0,
        }

        # Si hay datos de departamento
        if "departamento" in group.columns:
            vehicle_data["departamento"] = str(group["departamento"].mode().iloc[0]) if not group["departamento"].mode().empty else "Sin Depto"

        # Si hay datos de conductor
        if "conductor" in group.columns:
            conductores = group["conductor"].dropna().unique()
            vehicle_data["conductor"] = str(conductores[0]) if len(conductores) > 0 else "No registrado"

        # Si hay datos de kilometraje, calcular rendimiento
        if "kilometraje" in group.columns:
            km_values = pd.to_numeric(group["kilometraje"], errors="coerce").dropna().sort_values()
            if len(km_values) >= 2:
                km_recorridos = float(km_values.iloc[-1] - km_values.iloc[0])
                if km_recorridos > 0 and vehicle_data["total_litros"] > 0:
                    vehicle_data["km_recorridos"] = round(km_recorridos, 0)
                    vehicle_data["rendimiento_km_litro"] = round(km_recorridos / vehicle_data["total_litros"], 2)

        # Si Copec provee rendimiento directamente
        if "rendimiento" in group.columns and "rendimiento_km_litro" not in vehicle_data:
            rend_values = pd.to_numeric(group["rendimiento"], errors="coerce").dropna()
            if len(rend_values) > 0:
                vehicle_data["rendimiento_km_litro"] = round(float(rend_values.mean()), 2)

        # Estaciones frecuentes
        if "estacion" in group.columns:
            estacion_freq = group["estacion"].value_counts().head(3)
            vehicle_data["estaciones_frecuentes"] = {str(k): int(v) for k, v in estacion_freq.items()}

        vehicles[patente_str] = vehicle_data

    return vehicles


def generate_summary(df, vehicles):
    """Genera el resumen ejecutivo."""
    summary = {
        "periodo": "",
        "fecha_generacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "total_vehiculos": len(vehicles),
        "total_cargas": int(df.shape[0]),
        "total_litros": round(float(df["litros"].sum()), 2) if "litros" in df.columns else 0,
        "total_monto": round(float(df["monto"].sum()), 0) if "monto" in df.columns else 0,
        "promedio_litros_vehiculo": 0,
        "promedio_monto_vehiculo": 0,
    }

    # Calcular periodo
    if "fecha" in df.columns:
        try:
            df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True, errors="coerce")
            fecha_min = df["fecha"].min()
            fecha_max = df["fecha"].max()
            if pd.notna(fecha_min) and pd.notna(fecha_max):
                meses_es = {
                    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
                    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
                    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
                }
                summary["periodo"] = f"{meses_es.get(fecha_min.month, '')} {fecha_min.year}"
                if fecha_min.month != fecha_max.month:
                    summary["periodo"] = f"{meses_es.get(fecha_min.month, '')} - {meses_es.get(fecha_max.month, '')} {fecha_max.year}"
        except Exception:
            pass

    if not summary["periodo"]:
        now = datetime.now()
        meses_es = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        summary["periodo"] = f"{meses_es.get(now.month, '')} {now.year}"

    if summary["total_vehiculos"] > 0:
        summary["promedio_litros_vehiculo"] = round(summary["total_litros"] / summary["total_vehiculos"], 2)
        summary["promedio_monto_vehiculo"] = round(summary["total_monto"] / summary["total_vehiculos"], 0)

    return summary


def generate_department_summary(df):
    """Genera resumen por departamento."""
    if "departamento" not in df.columns:
        return []

    dept_data = []
    grouped = df.groupby("departamento")

    for dept, group in grouped:
        dept_str = str(dept).strip()
        if not dept_str or dept_str == "nan":
            continue

        dept_info = {
            "departamento": dept_str,
            "total_litros": round(float(group["litros"].sum()), 2) if "litros" in group.columns else 0,
            "total_monto": round(float(group["monto"].sum()), 0) if "monto" in group.columns else 0,
            "num_vehiculos": int(group["patente"].nunique()) if "patente" in group.columns else 0,
            "num_cargas": len(group),
        }
        dept_data.append(dept_info)

    # Ordenar por monto descendente
    dept_data.sort(key=lambda x: x["total_monto"], reverse=True)
    return dept_data


def generate_daily_trend(df):
    """Genera datos de tendencia diaria de consumo."""
    if "fecha" not in df.columns:
        return []

    try:
        df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True, errors="coerce")
        daily = df.groupby(df["fecha"].dt.date).agg(
            litros=("litros", "sum") if "litros" in df.columns else ("patente", "count"),
            monto=("monto", "sum") if "monto" in df.columns else ("patente", "count"),
            cargas=("patente", "count")
        ).reset_index()

        trend = []
        for _, row in daily.iterrows():
            trend.append({
                "fecha": str(row["fecha"]),
                "litros": round(float(row["litros"]), 2),
                "monto": round(float(row["monto"]), 0),
                "cargas": int(row["cargas"]),
            })
        return trend
    except Exception:
        return []


def generate_top_consumers(vehicles, top_n=10):
    """Genera ranking de vehículos con mayor consumo."""
    sorted_vehicles = sorted(vehicles.values(), key=lambda x: x["total_litros"], reverse=True)
    return sorted_vehicles[:top_n]


def clean_number(val):
    """Convierte número en formato chileno (1.234,56) a float estándar."""
    val = str(val).strip()
    if val in ("", "nan", "None", "-", "NaN", "none"):
        return None
    if "," in val:
        # Formato chileno: 1.234,56 → 1234.56
        val = val.replace(".", "").replace(",", ".")
    try:
        return round(float(val), 2)
    except (ValueError, TypeError):
        return None


# Columnas que deben almacenarse como float en transacciones
NUMERIC_TX_COLS = {"litros", "monto", "kilometraje", "rendimiento", "precio_unitario"}


def extract_transactions(df):
    """Extrae transacciones individuales del DataFrame para acumulación histórica.
    IMPORTANTE: convierte números chilenos (ej: '34,98') a float ANTES de almacenar."""
    transactions = []
    for _, row in df.iterrows():
        tx = {}
        for col in ["fecha", "patente", "departamento", "estacion", "producto",
                     "litros", "monto", "kilometraje", "conductor", "rendimiento",
                     "precio_unitario", "hora", "tarjeta"]:
            if col in df.columns:
                val = row[col]
                if pd.isna(val):
                    tx[col] = None
                elif col in NUMERIC_TX_COLS:
                    # Siempre limpiar formato chileno para columnas numéricas
                    if isinstance(val, (int, float, np.integer, np.floating)):
                        tx[col] = round(float(val), 2)
                    else:
                        tx[col] = clean_number(val)
                elif isinstance(val, (np.integer, np.floating)):
                    tx[col] = round(float(val), 2)
                elif isinstance(val, pd.Timestamp):
                    tx[col] = val.strftime("%Y-%m-%d")
                else:
                    tx[col] = str(val).strip()
        # Normalizar fecha ANTES de generar key
        if tx.get("fecha"):
            try:
                fecha_dt = pd.to_datetime(tx["fecha"], dayfirst=True, errors="coerce")
                if pd.notna(fecha_dt):
                    tx["mes"] = fecha_dt.strftime("%Y-%m")
                    tx["fecha"] = fecha_dt.strftime("%Y-%m-%d")
            except Exception:
                tx["mes"] = None
        # Generar clave única para deduplicación (después de normalizar fecha y números)
        tx["_key"] = f"{tx.get('fecha','')}__{tx.get('patente','')}__{tx.get('litros','')}__{tx.get('monto','')}__{tx.get('hora','')}"
        transactions.append(tx)
    return transactions


def load_accumulated_transactions(filepath):
    """Carga transacciones acumuladas de ejecuciones anteriores."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"[INFO] Transacciones históricas cargadas: {len(data)} registros")
                return data
        except Exception as e:
            print(f"[WARN] No se pudo leer historial: {e}")
    return []


def merge_transactions(existing, new_txs):
    """Combina transacciones existentes con nuevas, evitando duplicados."""
    existing_keys = {tx.get("_key") for tx in existing if tx.get("_key")}
    added = 0
    for tx in new_txs:
        if tx.get("_key") and tx["_key"] not in existing_keys:
            existing.append(tx)
            existing_keys.add(tx["_key"])
            added += 1
    print(f"[INFO] Transacciones nuevas agregadas: {added}, total acumulado: {len(existing)}")
    return existing


def build_report_from_transactions(transactions, filter_month=None):
    """Construye report_data a partir de transacciones (opcionalmente filtradas por mes)."""
    if filter_month:
        txs = [t for t in transactions if t.get("mes") == filter_month]
    else:
        txs = transactions

    if not txs:
        return None

    # Convertir a DataFrame para reusar lógica existente
    df = pd.DataFrame(txs)
    for col in ["litros", "monto", "kilometraje", "rendimiento", "precio_unitario"]:
        if col in df.columns:
            # Limpiar formato chileno si queda alguno
            df[col] = df[col].apply(lambda v: clean_number(v) if isinstance(v, str) else v)
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    vehicles = process_vehicle_data(df)
    summary = generate_summary(df, vehicles)
    departments = generate_department_summary(df)
    daily_trend = generate_daily_trend(df)
    top_consumers = generate_top_consumers(vehicles)

    return {
        "summary": summary,
        "vehicles": vehicles,
        "departments": departments,
        "daily_trend": daily_trend,
        "top_consumers": top_consumers,
    }


def find_all_excel_files(data_dir="data"):
    """Encuentra TODOS los archivos Excel en el directorio de datos."""
    files = []
    if os.path.isdir(data_dir):
        for f in os.listdir(data_dir):
            if f.lower().endswith((".xlsx", ".xls", ".csv")):
                files.append(os.path.join(data_dir, f))
    files.sort(key=os.path.getmtime)
    return files


def main():
    """Función principal de procesamiento."""
    data_dir = os.environ.get("DATA_DIR", "data")
    output_dir = os.environ.get("OUTPUT_DIR", "data")
    process_all = os.environ.get("PROCESS_ALL_FILES", "false").lower() == "true"

    # Cargar historial existente
    history_path = os.path.join(output_dir, "all_transactions.json")
    accumulated = load_accumulated_transactions(history_path)

    # Procesar uno o todos los archivos
    if process_all:
        all_files = find_all_excel_files(data_dir)
        print(f"[INFO] Modo histórico: procesando {len(all_files)} archivo(s)...")
        for fp in all_files:
            print(f"\n--- Procesando: {os.path.basename(fp)} ---")
            try:
                df = load_data(fp)
                new_txs = extract_transactions(df)
                print(f"[INFO] Transacciones extraídas: {len(new_txs)}")
                accumulated = merge_transactions(accumulated, new_txs)
            except Exception as e:
                print(f"[WARN] Error procesando {fp}: {e}")
    else:
        filepath = find_excel_file(data_dir)
        df = load_data(filepath)
        new_transactions = extract_transactions(df)
        print(f"[INFO] Transacciones extraídas del archivo: {len(new_transactions)}")
        accumulated = merge_transactions(accumulated, new_transactions)

    # Guardar historial acumulado
    os.makedirs(output_dir, exist_ok=True)
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(accumulated, f, ensure_ascii=False, indent=2)

    # Obtener meses disponibles
    months = sorted(set(t["mes"] for t in accumulated if t.get("mes")))
    print(f"[INFO] Meses disponibles: {months}")

    # Migrar transacciones con formato chileno antiguo (ej: "34,98" → 34.98)
    migrated = 0
    for tx in accumulated:
        for col in NUMERIC_TX_COLS:
            val = tx.get(col)
            if isinstance(val, str):
                tx[col] = clean_number(val)
                migrated += 1
        # Regenerar _key con valores limpios
        tx["_key"] = f"{tx.get('fecha','')}__{tx.get('patente','')}__{tx.get('litros','')}__{tx.get('monto','')}__{tx.get('hora','')}"
    if migrated > 0:
        # Deduplicar por _key regenerado
        seen_keys = set()
        deduped = []
        for tx in accumulated:
            k = tx.get("_key", "")
            if k not in seen_keys:
                seen_keys.add(k)
                deduped.append(tx)
        removed = len(accumulated) - len(deduped)
        accumulated = deduped
        print(f"[INFO] Migrados {migrated} valores numéricos. Eliminados {removed} duplicados.")
        # Re-guardar historial limpio
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(accumulated, f, ensure_ascii=False, indent=2)

    # Construir reporte a partir de TODAS las transacciones acumuladas
    all_df = pd.DataFrame(accumulated)
    for col in ["litros", "monto", "kilometraje", "rendimiento", "precio_unitario"]:
        if col in all_df.columns:
            all_df[col] = pd.to_numeric(all_df[col], errors="coerce").fillna(0)
    if "fecha" in all_df.columns:
        all_df["fecha"] = pd.to_datetime(all_df["fecha"], errors="coerce")

    vehicles = process_vehicle_data(all_df)
    summary = generate_summary(all_df, vehicles)
    departments = generate_department_summary(all_df)
    daily_trend = generate_daily_trend(all_df)
    top_consumers = generate_top_consumers(vehicles)

    # Generar JSON con todos los datos + transacciones históricas
    report_data = {
        "metadata": {
            "generado": datetime.now().isoformat(),
            "archivo_fuente": "acumulado_historico",
            "total_registros": len(accumulated),
        },
        "months_available": months,
        "all_transactions": accumulated,
        "summary": summary,
        "vehicles": vehicles,
        "departments": departments,
        "daily_trend": daily_trend,
        "top_consumers": top_consumers,
    }

    # Guardar JSON
    output_path = os.path.join(output_dir, "report_data.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Reporte generado: {output_path}")
    print(f"  - Vehículos: {summary['total_vehiculos']}")
    print(f"  - Total litros: {summary['total_litros']}")
    print(f"  - Total monto: ${summary['total_monto']:,.0f}")
    print(f"  - Periodo: {summary['periodo']}")
    print(f"  - Meses acumulados: {', '.join(months)}")


if __name__ == "__main__":
    main()