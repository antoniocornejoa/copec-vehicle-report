"""Genera datos de ejemplo para previsualizar el reporte."""
import json
import random
import os

random.seed(42)

patentes = [
    "GGKL-45", "HRTW-12", "JKPS-78", "LMDN-33", "BCTF-91",
    "WPRT-56", "XKVL-23", "DFMN-67", "RQST-44", "YCLP-88",
    "HNVW-15", "TMGK-72", "PSDF-39", "VLKJ-61", "ZCXW-27"
]
departamentos = ["CASA MATRIZ", "OBRA TALCA SUR", "OBRA CONSTITUCION", "OBRA LINARES"]
conductores = [
    "Juan Perez", "Carlos Munoz", "Pedro Gonzalez", "Luis Rodriguez",
    "Miguel Soto", "Andres Silva", "Felipe Diaz", "Roberto Fuentes",
    "Pablo Rojas", "Diego Morales", "Sergio Vargas", "Raul Contreras",
    "Hugo Espinoza", "Oscar Tapia", "Mario Campos"
]
estaciones = [
    "COPEC Talca Centro", "COPEC Ruta 5 Sur km245", "COPEC Linares",
    "COPEC Constitucion", "COPEC San Clemente", "COPEC Maule"
]

vehicles = {}
for i, pat in enumerate(patentes):
    dept = departamentos[i % len(departamentos)]
    n_cargas = random.randint(4, 18)
    litros_carga = random.uniform(30, 80)
    total_litros = round(n_cargas * litros_carga, 2)
    precio_litro = random.uniform(950, 1050)
    total_monto = round(total_litros * precio_litro, 0)
    km_base = random.randint(50000, 150000)
    km_final = km_base + random.randint(800, 4000)
    km_recorridos = km_final - km_base
    rendimiento = round(km_recorridos / total_litros, 2) if total_litros > 0 else 0

    vehicles[pat] = {
        "patente": pat,
        "departamento": dept,
        "conductor": conductores[i],
        "total_litros": total_litros,
        "total_monto": total_monto,
        "num_cargas": n_cargas,
        "promedio_litros_carga": round(total_litros / n_cargas, 2),
        "promedio_monto_carga": round(total_monto / n_cargas, 0),
        "km_recorridos": km_recorridos,
        "rendimiento_km_litro": rendimiento,
        "estaciones_frecuentes": {random.choice(estaciones): random.randint(2, 8)}
    }

total_litros = sum(v["total_litros"] for v in vehicles.values())
total_monto = sum(v["total_monto"] for v in vehicles.values())
total_cargas = sum(v["num_cargas"] for v in vehicles.values())

departments = []
for dept in departamentos:
    dept_vehicles = {k: v for k, v in vehicles.items() if v["departamento"] == dept}
    departments.append({
        "departamento": dept,
        "total_litros": round(sum(v["total_litros"] for v in dept_vehicles.values()), 2),
        "total_monto": round(sum(v["total_monto"] for v in dept_vehicles.values()), 0),
        "num_vehiculos": len(dept_vehicles),
        "num_cargas": sum(v["num_cargas"] for v in dept_vehicles.values()),
    })
departments.sort(key=lambda x: x["total_monto"], reverse=True)

daily_trend = []
for day in range(1, 32):
    daily_trend.append({
        "fecha": f"2026-03-{day:02d}",
        "litros": round(random.uniform(100, 600), 2),
        "monto": round(random.uniform(100000, 600000), 0),
        "cargas": random.randint(2, 12),
    })

top_consumers = sorted(vehicles.values(), key=lambda x: x["total_litros"], reverse=True)[:10]

report_data = {
    "metadata": {
        "generado": "2026-03-31T15:20:00",
        "archivo_fuente": "transacciones_marzo_2026.xlsx",
        "total_registros": total_cargas,
    },
    "summary": {
        "periodo": "Marzo 2026",
        "fecha_generacion": "31/03/2026 15:20",
        "total_vehiculos": len(vehicles),
        "total_cargas": total_cargas,
        "total_litros": round(total_litros, 2),
        "total_monto": round(total_monto, 0),
        "promedio_litros_vehiculo": round(total_litros / len(vehicles), 2),
        "promedio_monto_vehiculo": round(total_monto / len(vehicles), 0),
    },
    "vehicles": vehicles,
    "departments": departments,
    "daily_trend": daily_trend,
    "top_consumers": top_consumers,
}

os.makedirs("data", exist_ok=True)
with open("data/report_data.json", "w", encoding="utf-8") as f:
    json.dump(report_data, f, ensure_ascii=False, indent=2)

print("[OK] Datos de ejemplo generados en data/report_data.json")
