#!/usr/bin/env python3
"""
Generates an HTML dashboard report for vehicle fuel consumption tracking.
Reads data/report_data.json and outputs docs/index.html.
"""

import json
import os
import sys


def format_number(n):
    """Format number with Chilean convention: dots for thousands, comma for decimals."""
    if n is None:
        return "0"
    if isinstance(n, float):
        integer_part = int(n)
        decimal_part = round(n - integer_part, 2)
        dec_str = f"{decimal_part:.2f}"[2:]
        int_str = f"{integer_part:,}".replace(",", ".")
        return f"{int_str},{dec_str}"
    else:
        return f"{int(n):,}".replace(",", ".")


def format_money(n):
    """Format as Chilean currency: $1.234.567"""
    if n is None:
        return "$0"
    return "$" + f"{int(round(n)):,}".replace(",", ".")


def generate_html(report_data):
    """Generate complete HTML dashboard from report data."""
    json_data = json.dumps(report_data, ensure_ascii=False, default=str)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Informe de Rendimiento Vehicular</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root {{
    --primary: #0d9488;
    --primary-light: #14b8a6;
    --primary-dark: #0f766e;
    --accent: #c4b515;
    --accent-dark: #a39a10;
    --bg: #f0fdfa;
    --bg-card: #ffffff;
    --text: #1e293b;
    --text-light: #64748b;
    --border: #e2e8f0;
    --success: #16a34a;
    --danger: #dc2626;
    --shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06);
    --radius: 12px;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
.container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
/* Header */
.header {{ background: linear-gradient(135deg, var(--primary-dark), var(--primary)); color: white; padding: 30px; border-radius: var(--radius); margin-bottom: 24px; box-shadow: var(--shadow-md); }}
.header h1 {{ font-size: 1.8rem; font-weight: 700; margin-bottom: 4px; }}
.header .subtitle {{ opacity: 0.9; font-size: 0.95rem; margin-bottom: 16px; }}
.header-actions {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }}
.badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; background: rgba(255,255,255,0.2); color: white; }}
.badge-online::before {{ content: ''; width: 8px; height: 8px; border-radius: 50%; background: #4ade80; display: inline-block; animation: pulse 2s infinite; }}
@keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}
.export-btn {{ padding: 8px 16px; border: none; border-radius: 8px; font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px; }}
.btn-print {{ background: rgba(255,255,255,0.2); color: white; }}
.btn-print:hover {{ background: rgba(255,255,255,0.3); }}
.btn-csv {{ background: rgba(255,255,255,0.2); color: white; }}
.btn-csv:hover {{ background: rgba(255,255,255,0.3); }}
.btn-update {{ background: var(--accent); color: #1a1a00; }}
.btn-update:hover {{ background: var(--accent-dark); }}
.btn-update.loading {{ opacity: 0.7; pointer-events: none; }}
.btn-update.success {{ background: var(--success); color: white; }}
.btn-update.error {{ background: var(--danger); color: white; }}
/* Filter */
.filter-bar {{ background: var(--bg-card); border-radius: var(--radius); padding: 16px 20px; margin-bottom: 24px; box-shadow: var(--shadow); display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }}
.filter-bar label {{ font-weight: 600; font-size: 0.9rem; color: var(--text-light); }}
.filter-bar select, .filter-bar inputt {{ padding: 8px 14px; border: 1px solid var(--border); border-radius: 8px; font-size: 0.9rem; background: white; color: var(--text); }}
.filter-bar select:focus, .filter-bar input:focus {{ outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(13,148,136,0.1); }}
/* KPI Grid */
.kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
.kpi-card {{ background: var(--bg-card); border-radius: var(--radius); padding: 20px; box-shadow: var(--shadow); border-left: 4px solid var(--primary); }}
.kpi-card .kpi-label {{ font-size: 0.8rem; color: var(--text-light); text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 6px; }}
.kpi-card .kpi-value {{ font-size: 1.6rem; font-weight: 700; color: var(--text); }}
/* Comparison Section */
.comparison-section {{ background: var(--bg-card); border-radius: var(--radius); padding: 24px; margin-bottom: 24px; box-shadow: var(--shadow); }}
.comparison-section h3 {{ font-size: 1.1rem; color: var(--text); margin-bottom: 16px; font-weight: 700; }}
.comparison-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 20px; }}
.comp-card {{ background: var(--bg); border-radius: 10px; padding: 16px; position: relative; }}
.comp-card .comp-label {{ font-size: 0.78rem; color: var(--text-light); text-transform: uppercase; font-weight: 600; margin-bottom: 8px; }}
.comp-card .comp-current {{ font-size: 1.3rem; font-weight: 700; color: var(--text); }}
.comp-card .comp-previous {{ font-size: 0.82rem; color: var(--text-light); margin-top: 4px; }}
.comp-card .comp-change {{ display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 12px; font-size: 0.78rem; font-weight: 600; margin-top: 6px; }}
.comp-change.positive {{ background: #dcfce7; color: var(--success); }}
.comp-change.negative {{ background: #fef2f2; color: var(--danger); }}
.comp-change.neutral {{ background: #f1f5f9; color: var(--text-light); }}
#comparisonChart {{ max-height: 250px; }}
/* Monthly Overview Table */
.monthly-table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
.monthly-table th {{ background: var(--bg); padding: 10px 14px; text-align: left; font-weight: 600; color: var(--text-light); border-bottom: 2px solid var(--border); }}
.monthly-table td {{ padding: 10px 14px; border-bottom: 1px solid var(--border); }}
.monthly-table tr:hover {{ background: var(--bg); }}
.monthly-table .highlight-max {{ background: #fef2f2; }}
.monthly-table .highlight-min {{ background: #dcfce7; }}
.trend-indicator {{ display: inline-block; width: 0; height: 0; margin-left: 6px; }}
.trend-up {{ border-left: 5px solid transparent; border-right: 5px solid transparent; border-bottom: 8px solid var(--danger); }}
.trend-down {{ border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 8px solid var(--success); }}
/* Charts */
.charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
.chart-card {{ background: var(--bg-card); border-radius: var(--radius); padding: 20px; box-shadow: var(--shadow); }}
.chart-card h3 {{ font-size: 1rem; font-weight: 600; margin-bottom: 14px; color: var(--text); }}
.chart-card canvas {{ width: 100% !important; }}
.chart-full {{ grid-column: 1 / -1; }}
/* Tabs */
.tabs {{ margin-bottom: 24px; }}
.tab-buttons {{ display: flex; gap: 0; background: var(--bg-card); border-radius: var(--radius) var(--radius) 0 0; overflow: hidden; box-shadow: var(--shadow); }}
.tab-btn {{ flex: 1; padding: 14px; border: none; background: transparent; font-size: 0.9rem; font-weight: 600; color: var(--text-light); cursor: pointer; transition: all 0.2s; border-bottom: 3px solid transparent; }}
.tab-btn.active {{ color: var(--primary); border-bottom-color: var(--primary); background: var(--bg-card); }}
.tab-btn:hover {{ background: var(--bg); }}
.tab-content {{ background: var(--bg-card); border-radius: 0 0 var(--radius) var(--radius); padding: 20px; box-shadow: var(--shadow); display: none; }}
.tab-content.active {{ display: block; }}
/* Tables */
.table-controls {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 14px; align-items: center; }}
.data-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
.data-table th {{ background: var(--bg); padding: 10px 12px; text-align: left; font-weight: 600; color: var(--text-light); border-bottom: 2px solid var(--border); cursor: pointer; white-space: nowrap; user-select: none; position: relative; }}
.data-table th:hover {{ background: #e2e8f0; }}
.data-table th .sort-arrow {{ margin-left: 4px; font-size: 0.7rem; opacity: 0.4; }}
.data-table th.sorted-asc .sort-arrow, .data-table th.sorted-desc .sort-arrow {{ opacity: 1; color: var(--primary); }}
.data-table td {{ padding: 9px 12px; border-bottom: 1px solid var(--border); }}
.data-table tr:hover {{ background: var(--bg); }}
.data-table tr:nth-child(even) {{ background: #f8fafc; }}
.data-table tr:nth-child(even):hover {{ background: var(--bg); }}
.json-preview {{ background: #1e293b; color: #e2e8f0; padding: 20px; border-radius: 8px; font-family: 'Courier New', monospace; font-size: 0.8rem; max-height: 500px; overflow: auto; white-space: pre-wrap; word-break: break-all; }}
/* Responsive */
@media (max-width: 900px) {{
    .charts-grid {{ grid-template-columns: 1fr; }}
    .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .comparison-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}
@media (max-width: 600px) {{
    .container {{ padding: 10px; }}
    .kpi-grid {{ grid-template-columns: 1fr; }}
    .comparison-grid {{ grid-template-columns: 1fr; }}
    .header h1 {{ font-size: 1.3rem; }}
    .data-table {{ font-size: 0.75rem; }}
    .data-table th, .data-table td {{ padding: 6px 8px; }}
}}
/* Print */
@media print {{
    body {{ background: white; }}
    .filter-bar, .export-btn, .btn-update, .btn-print, .btn-csv, .tab-buttons, .table-controls, #monthFilter {{ display: none !important; }}
    .header {{ background: var(--primary) !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .tab-content {{ display: block !important; page-break-inside: avoid; }}
    .charts-grid {{ page-break-inside: avoid; }}
    .chart-card {{ page-break-inside: avoid; }}
    .kpi-card {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
}}
</style>
</head>
<body>
<div class="container">
    <!-- Header -->
    <div class="header">
        <h1>Informe de Rendimiento Vehicular</h1>
        <div class="subtitle" id="headerSubtitle"></div>
        <div class="header-actions">
            <span class="badge badge-online">En linea</span>
            <button class="export-btn btn-print" onclick="window.print()">&#128424; Imprimir</button>
            <button class="export-btn btn-csv" onclick="exportAllCSV()">&#128229; Exportar CSV</button>
            <button class="export-btn btn-update" id="btnUpdate" onclick="triggerWorkflow()">&#128260; Actualizar Datos</button>
        </div>
    </div>

    <!-- Month Filter -->
    <div class="filter-bar">
        <label for="monthFilter">Filtrar por mes:</label>
        <select id="monthFilter" onchange="onMonthChange()"></select>
    </div>

    <!-- KPI Cards -->
    <div class="kpi-grid" id="kpiGrid"></div>

    <!-- Monthly Comparison / Overview -->
    <div class="comparison-section" id="comparisonSection"></div>

    <!-- Charts -->
    <div class="charts-grid">
        <div class="chart-card">
            <h3>Consumo por Departamento</h3>
            <canvas id="chartDept"></canvas>
        </div>
        <div class="chart-card">
            <h3>Top 10 Vehiculos - Mayor Consumo</h3>
            <canvas id="chartTop"></canvas>
        </div>
        <div class="chart-card chart-full">
            <h3>Tendencia Diaria</h3>
            <canvas id="chartTrend"></canvas>
        </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
        <div class="tab-buttons">
            <button class="tab-btn active" onclick="switchTab('vehicles')">Vehiculos</button>
            <button class="tab-btn" onclick="switchTab('departments')">Departamentos</button>
            <button class="tab-btn" onclick="switchTab('data')">Datos</button>
        </div>
        <div class="tab-content active" id="tab-vehicles">
            <div class="table-controls">
                <input type="text" id="searchVehicle" placeholder="Buscar patente o conductor..." oninput="renderVehicleTable(currentFilteredData.vehicles)">
                <select id="deptFilterSelect" onchange="renderVehicleTable(currentFilteredData.vehicles)">
                    <option value="">Todos los departamentos</option>
                </select>
                <button class="export-btn btn-csv" onclick="exportTableCSV('vehicleTable', 'vehiculos')">&#128229; CSV</button>
            </div>
            <div style="overflow-x:auto;">
                <table class="data-table" id="vehicleTable">
                    <thead>
                        <tr>
                            <th onclick="sortTable('vehicleTable', 0, 'num')"># <span class="sort-arrow">&#9650;&#9660;</span></th>
                            <th onclick="sortTable('vehicleTable', 1, 'str')">Patente <span class="sort-arrow">&#9650;&#9660;</span></th>
                            <th onclick="sortTable('vehicleTable', 2, 'str')">Departamento <span class="sort-arrow">&#9650;&#9660;</span></th>
                            <th onclick="sortTable('vehicleTable', 3, 'str')">Conductor <span class="sort-arrow">&#9650;&#9660;</span></th>
                            <th onclick="sortTable('vehicleTable', 4, 'num')">Litros <span class="sort-arrow">&#9650;&#9660;</span></th>
                            <th onclick="sortTable('vehicleTable', 5, 'num')">Monto <span class="sort-arrow">&#9650;&#9660;</span></th>
                            <th onclick="sortTable('vehicleTable', 6, 'num')">Cargas <span class="sort-arrow">&#9650;&#9660;</span></th>
                            <th onclick="sortTable('vehicleTable', 7, 'num')">Prom Lt/Carga <span class="sort-arrow">&#9650;&#9660;</span></th>
                            <th onclick="sortTable('vehicleTable', 8, 'num')">Km Recorridos <span class="sort-arrow">&#9650;&#9660;</span></th>
                            <th onclick="sortTable('vehicleTable', 9, 'num')">Rendimiento km/L <span class="sort-arrow">&#9650;&#9660;</span></th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
        <div class="tab-content" id="tab-departments">
            <div class="table-controls">
                <button class="export-btn btn-csv" onclick="exportTableCSV('deptTable', 'departamentos')">&#128229; CSV</button>
            </div>
            <div style="overflow-x:auto;">
                <table class="data-table" id="deptTable">
                    <thead>
                        <tr>
                            <th onclick="sortTable('deptTable', 0, 'num')"># <span class="sort-arrow">&#9650;&#9660;</span></th>
                            <th onclick="sortTable('deptTable', 1, 'str')">Departamento <span class="sort-arrow">&#9650;&#9660;</span></th>
                            <th onclick="sortTable('deptTable', 2, 'num')">Litros <span class="sort-arrow">&#9650;&#9660;</span></th>
                            <th onclick="sortTable('deptTable', 3, 'num')">Monto <span class="sort-arrow">&#9650;&#9660;</span></th>
                            <th onclick="sortTable('deptTable', 4, 'num')">Vehiculos <span class="sort-arrow">&#9650;&#9660;</span></th>
                            <th onclick="sortTable('deptTable', 5, 'num')">Cargas <span class="sort-arrow">&#9650;&#9660;</span></th>
                            <th onclick="sortTable('deptTable', 6, 'num')">Prom Lt/Vehiculo <span class="sort-arrow">&#9650;&#9660;</span></th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
        <div class="tab-content" id="tab-data">
            <div class="json-preview" id="jsonPreview"></div>
        </div>
    </div>
</div>

<script>
// ==================== DATA ====================
const reportData = {json_data};

const MONTH_NAMES = {{
    '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
    '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
    '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
}};

let currentFilteredData = {{}};
let chartDept = null, chartTop = null, chartTrend = null, compChart = null;

// ==================== FORMATTING ====================
function fmtNum(n, decimals) {{
    if (n == null || isNaN(n)) return '0';
    decimals = decimals !== undefined ? decimals : 2;
    const parts = Number(n).toFixed(decimals).split('.');
    const intPart = parts[0].replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, '.');
    if (decimals === 0) return intPart;
    return intPart + ',' + parts[1];
}}

function fmtMoney(n) {{
    if (n == null || isNaN(n)) return '$0';
    return '$' + fmtNum(Math.round(n), 0);
}}

function parseNumericValue(val) {{
    if (typeof val === 'number') return val;
    if (!val) return 0;
    let s = String(val).replace(/\\$/g, '').replace(/\\./g, '').replace(/,/g, '.');
    return parseFloat(s) || 0;
}}

function monthLabel(ym) {{
    if (!ym) return '';
    const parts = ym.split('-');
    return MONTH_NAMES[parts[1]] + ' ' + parts[0];
}}

// ==================== COMPUTATION ====================
function computeFromTransactions(txs) {{
    const summary = {{
        total_litros: 0, total_monto: 0, total_cargas: txs.length,
        total_vehiculos: 0, promedio_litros_vehiculo: 0, promedio_monto_vehiculo: 0
    }};
    const vehicleMap = {{}};
    const deptMap = {{}};
    const dailyMap = {{}};

    txs.forEach(function(tx) {{
        const litros = tx.litros || 0;
        const monto = tx.monto || 0;
        const km = tx.kilometraje || 0;
        const rendimiento = tx.rendimiento || 0;
        const patente = tx.patente || 'N/A';
        const dept = tx.departamento || 'N/A';
        const conductor = tx.conductor || 'N/A';
        const fecha = tx.fecha || '';

        summary.total_litros += litros;
        summary.total_monto += monto;

        if (!vehicleMap[patente]) {{
            vehicleMap[patente] = {{
                patente: patente, departamento: dept, conductor: conductor,
                total_litros: 0, total_monto: 0, num_cargas: 0,
                km_total: 0, rendimiento_sum: 0, rendimiento_count: 0,
                min_km: Infinity, max_km: 0
            }};
        }}
        const v = vehicleMap[patente];
        v.total_litros += litros;
        v.total_monto += monto;
        v.num_cargas += 1;
        if (km > 0) {{
            if (km < v.min_km) v.min_km = km;
            if (km > v.max_km) v.max_km = km;
        }}
        if (rendimiento > 0) {{
            v.rendimiento_sum += rendimiento;
            v.rendimiento_count += 1;
        }}
        if (!v.departamento || v.departamento === 'N/A') v.departamento = dept;
        if (!v.conductor || v.conductor === 'N/A') v.conductor = conductor;

        if (!deptMap[dept]) {{
            deptMap[dept] = {{ departamento: dept, total_litros: 0, total_monto: 0, num_cargas: 0, vehiculos: new Set() }};
        }}
        deptMap[dept].total_litros += litros;
        deptMap[dept].total_monto += monto;
        deptMap[dept].num_cargas += 1;
        deptMap[dept].vehiculos.add(patente);

        if (fecha) {{
            if (!dailyMap[fecha]) {{
                dailyMap[fecha] = {{ fecha: fecha, litros: 0, monto: 0, cargas: 0 }};
            }}
            dailyMap[fecha].litros += litros;
            dailyMap[fecha].monto += monto;
            dailyMap[fecha].cargas += 1;
        }}
    }});

    const vehicles = Object.values(vehicleMap).map(function(v) {{
        v.prom_litros_carga = v.num_cargas > 0 ? v.total_litros / v.num_cargas : 0;
        v.km_recorridos = (v.max_km > 0 && v.min_km < Infinity) ? v.max_km - v.min_km : 0;
        v.rendimiento_avg = v.rendimiento_count > 0 ? v.rendimiento_sum / v.rendimiento_count : 0;
        return v;
    }});
    vehicles.sort(function(a, b) {{ return b.total_litros - a.total_litros; }});

    const departments = Object.values(deptMap).map(function(d) {{
        d.num_vehiculos = d.vehiculos.size;
        d.prom_litros_vehiculo = d.num_vehiculos > 0 ? d.total_litros / d.num_vehiculos : 0;
        delete d.vehiculos;
        return d;
    }});
    departments.sort(function(a, b) {{ return b.total_litros - a.total_litros; }});

    const daily_trend = Object.values(dailyMap);
    daily_trend.sort(function(a, b) {{ return a.fecha.localeCompare(b.fecha); }});

    const top_consumers = vehicles.slice(0, 10);

    summary.total_vehiculos = vehicles.length;
    summary.promedio_litros_vehiculo = summary.total_vehiculos > 0 ? summary.total_litros / summary.total_vehiculos : 0;
    summary.promedio_monto_vehiculo = summary.total_vehiculos > 0 ? summary.total_monto / summary.total_vehiculos : 0;

    return {{
        summary: summary,
        vehicles: vehicles,
        departments: departments,
        daily_trend: daily_trend,
        top_consumers: top_consumers
    }};
}}

function computeMonthData(month) {{
    const txs = reportData.all_transactions.filter(function(t) {{ return t.mes === month; }});
    return computeFromTransactions(txs);
}}

// ==================== RENDERING ====================
function renderKPIs(summary) {{
    const grid = document.getElementById('kpiGrid');
    const cards = [
        {{ label: 'Monto Total', value: fmtMoney(summary.total_monto) }},
        {{ label: 'Total Transacciones', value: fmtNum(summary.total_cargas, 0) }},
        {{ label: 'Vehiculos', value: fmtNum(summary.total_vehiculos, 0) }},
        {{ label: 'Litros Totales', value: fmtNum(summary.total_litros, 1) }},
        {{ label: 'Promedio Litros/Vehiculo', value: fmtNum(summary.promedio_litros_vehiculo, 1) }},
        {{ label: 'Gasto Promedio/Vehiculo', value: fmtMoney(summary.promedio_monto_vehiculo) }}
    ];
    grid.innerHTML = cards.map(function(c) {{
        return '<div class="kpi-card"><div class="kpi-label">' + c.label + '</div><div class="kpi-value">' + c.value + '</div></div>';
    }}).join('');
}}

function renderComparison(currentMonth, data) {{
    const section = document.getElementById('comparisonSection');
    const months = (reportData.months_available || []).slice().sort();
    const idx = months.indexOf(currentMonth);
    if (idx < 0) {{ section.innerHTML = ''; return; }}

    let prevMonth = idx > 0 ? months[idx - 1] : null;
    const curData = data.summary;

    section.innerHTML = '<h3>Comparacion Mensual: ' + monthLabel(currentMonth) +
        (prevMonth ? ' vs ' + monthLabel(prevMonth) : '') + '</h3>';

    if (!prevMonth) {{
        section.innerHTML += '<p style="color:var(--text-light);">No hay mes anterior disponible para comparar.</p>';
        return;
    }}

    const prevData = computeMonthData(prevMonth).summary;

    function pctChange(cur, prev) {{
        if (prev === 0) return cur > 0 ? 100 : 0;
        return ((cur - prev) / prev) * 100;
    }}

    function changeHTML(cur, prev, invertColor) {{
        const pct = pctChange(cur, prev);
        const arrow = pct > 0 ? '&#9650;' : pct < 0 ? '&#9660;' : '';
        let cls = 'neutral';
        if (pct !== 0) {{
            if (invertColor) {{
                cls = pct > 0 ? 'negative' : 'positive';
            }} else {{
                cls = pct > 0 ? 'positive' : 'negative';
            }}
        }}
        return '<span class="comp-change ' + cls + '">' + arrow + ' ' + fmtNum(Math.abs(pct), 1) + '%</span>';
    }}

    const metrics = [
        {{ label: 'Litros', cur: curData.total_litros, prev: prevData.total_litros, fmt: function(v) {{ return fmtNum(v, 1); }}, invert: true }},
        {{ label: 'Monto', cur: curData.total_monto, prev: prevData.total_monto, fmt: fmtMoney, invert: true }},
        {{ label: 'Cargas', cur: curData.total_cargas, prev: prevData.total_cargas, fmt: function(v) {{ return fmtNum(v, 0); }}, invert: false }},
        {{ label: 'Vehiculos', cur: curData.total_vehiculos, prev: prevData.total_vehiculos, fmt: function(v) {{ return fmtNum(v, 0); }}, invert: false }}
    ];

    let cardsHTML = '<div class="comparison-grid">';
    metrics.forEach(function(m) {{
        cardsHTML += '<div class="comp-card">' +
            '<div class="comp-label">' + m.label + '</div>' +
            '<div class="comp-current">' + m.fmt(m.cur) + '</div>' +
            '<div class="comp-previous">Anterior: ' + m.fmt(m.prev) + '</div>' +
            changeHTML(m.cur, m.prev, m.invert) +
            '</div>';
    }});
    cardsHTML += '</div>';
    section.innerHTML += cardsHTML;

    section.innerHTML += '<canvas id="comparisonChart"></canvas>';

    const ctx = document.getElementById('comparisonChart').getContext('2d');
    if (compChart) compChart.destroy();
    compChart = new Chart(ctx, {{
        type: 'bar',
        data: {{
            labels: ['Litros', 'Monto (miles)', 'Cargas', 'Vehiculos'],
            datasets: [
                {{
                    label: monthLabel(currentMonth),
                    data: [curData.total_litros, curData.total_monto / 1000, curData.total_cargas, curData.total_vehiculos],
                    backgroundColor: 'rgba(13,148,136,0.7)',
                    borderRadius: 6
                }},
                {{
                    label: monthLabel(prevMonth),
                    data: [prevData.total_litros, prevData.total_monto / 1000, prevData.total_cargas, prevData.total_vehiculos],
                    backgroundColor: 'rgba(196,181,21,0.7)',
                    borderRadius: 6
                }}
            ]
        }},
        options: {{
            responsive: true,
            plugins: {{ legend: {{ position: 'top' }} }},
            scales: {{ y: {{ beginAtZero: true }} }}
        }}
    }});
}}

function renderMonthlyOverview(allMonths) {{
    const section = document.getElementById('comparisonSection');
    section.innerHTML = '<h3>Resumen por Mes</h3>';

    const monthsData = allMonths.map(function(m) {{
        const d = computeMonthData(m);
        return {{ month: m, summary: d.summary }};
    }});

    let maxLitros = 0, minLitros = Infinity, maxMonth = '', minMonth = '';
    monthsData.forEach(function(md) {{
        if (md.summary.total_litros > maxLitros) {{ maxLitros = md.summary.total_litros; maxMonth = md.month; }}
        if (md.summary.total_litros < minLitros) {{ minLitros = md.summary.total_litros; minMonth = md.month; }}
    }});

    let tableHTML = '<table class="monthly-table"><thead><tr>' +
        '<th>Mes</th><th>Litros</th><th>Monto</th><th>Cargas</th><th>Vehiculos</th><th>Prom Lt/Vehiculo</th>' +
        '</tr></thead><tbody>';

    monthsData.forEach(function(md, i) {{
        let rowClass = '';
        if (md.month === maxMonth) rowClass = 'highlight-max';
        else if (md.month === minMonth) rowClass = 'highlight-min';

        let trendHTML = '';
        if (i > 0) {{
            const prevLitros = monthsData[i - 1].summary.total_litros;
            if (md.summary.total_litros > prevLitros) trendHTML = '<span class="trend-indicator trend-up"></span>';
            else if (md.summary.total_litros < prevLitros) trendHTML = '<span class="trend-indicator trend-down"></span>';
        }}

        tableHTML += '<tr class="' + rowClass + '">' +
            '<td><strong>' + monthLabel(md.month) + '</strong>' + trendHTML + '</td>' +
            '<td>' + fmtNum(md.summary.total_litros, 1) + '</td>' +
            '<td>' + fmtMoney(md.summary.total_monto) + '</td>' +
            '<td>' + fmtNum(md.summary.total_cargas, 0) + '</td>' +
            '<td>' + fmtNum(md.summary.total_vehiculos, 0) + '</td>' +
            '<td>' + fmtNum(md.summary.promedio_litros_vehiculo, 1) + '</td>' +
            '</tr>';
    }});

    tableHTML += '</tbody></table>';
    section.innerHTML += tableHTML;

    if (maxMonth) {{
        section.innerHTML += '<p style="margin-top:12px;font-size:0.85rem;color:var(--text-light);">' +
            '<span style="display:inline-block;width:12px;height:12px;background:#fef2f2;border:1px solid #fca5a5;margin-right:4px;vertical-align:middle;"></span> Mayor consumo: ' + monthLabel(maxMonth) +
            ' &nbsp;&nbsp; <span style="display:inline-block;width:12px;height:12px;background:#dcfce7;border:1px solid #86efac;margin-right:4px;vertical-align:middle;"></span> Menor consumo: ' + monthLabel(minMonth) +
            '</p>';
    }}
}}

function renderVehicleTable(vehicles) {{
    const search = (document.getElementById('searchVehicle').value || '').toLowerCase();
    const deptFilter = document.getElementById('deptFilterSelect').value;

    let filtered = vehicles.filter(function(v) {{
        let matchSearch = true, matchDept = true;
        if (search) {{
            matchSearch = (v.patente || '').toLowerCase().indexOf(search) >= 0 ||
                          (v.conductor || '').toLowerCase().indexOf(search) >= 0;
        }}
        if (deptFilter) {{
            matchDept = v.departamento === deptFilter;
        }}
        return matchSearch && matchDept;
    }});

    const tbody = document.querySelector('#vehicleTable tbody');
    tbody.innerHTML = filtered.map(function(v, i) {{
        return '<tr>' +
            '<td>' + (i + 1) + '</td>' +
            '<td><strong>' + (v.patente || '') + '</strong></td>' +
            '<td>' + (v.departamento || '') + '</td>' +
            '<td>' + (v.conductor || '') + '</td>' +
            '<td>' + fmtNum(v.total_litros, 1) + '</td>' +
            '<td>' + fmtMoney(v.total_monto) + '</td>' +
            '<td>' + fmtNum(v.num_cargas, 0) + '</td>' +
            '<td>' + fmtNum(v.prom_litros_carga, 1) + '</td>' +
            '<td>' + fmtNum(v.km_recorridos, 0) + '</td>' +
            '<td>' + fmtNum(v.rendimiento_avg, 2) + '</td>' +
            '</tr>';
    }}).join('');
}}

function renderDeptTable(departments) {{
    const tbody = document.querySelector('#deptTable tbody');
    tbody.innerHTML = departments.map(function(d, i) {{
        return '<tr>' +
            '<td>' + (i + 1) + '</td>' +
            '<td><strong>' + (d.departamento || '') + '</strong></td>' +
            '<td>' + fmtNum(d.total_litros, 1) + '</td>' +
            '<td>' + fmtMoney(d.total_monto) + '</td>' +
            '<td>' + fmtNum(d.num_vehiculos, 0) + '</td>' +
            '<td>' + fmtNum(d.num_cargas, 0) + '</td>' +
            '<td>' + fmtNum(d.prom_litros_vehiculo, 1) + '</td>' +
            '</tr>';
    }}).join('');
}}

function renderCharts(data) {{
    // Department chart
    const depts = data.departments.slice(0, 15);
    const deptLabels = depts.map(function(d) {{ return d.departamento; }});
    const deptLitros = depts.map(function(d) {{ return d.total_litros; }});
    const deptMonto = depts.map(function(d) {{ return d.total_monto; }});

    if (chartDept) chartDept.destroy();
    chartDept = new Chart(document.getElementById('chartDept').getContext('2d'), {{
        type: 'bar',
        data: {{
            labels: deptLabels,
            datasets: [
                {{
                    label: 'Litros',
                    data: deptLitros,
                    backgroundColor: 'rgba(13,148,136,0.7)',
                    borderRadius: 6,
                    yAxisID: 'y'
                }},
                {{
                    label: 'Monto ($)',
                    data: deptMonto,
                    backgroundColor: 'rgba(196,181,21,0.5)',
                    borderRadius: 6,
                    yAxisID: 'y1'
                }}
            ]
        }},
        options: {{
            responsive: true,
            plugins: {{ legend: {{ position: 'top' }} }},
            scales: {{
                y: {{ beginAtZero: true, position: 'left', title: {{ display: true, text: 'Litros' }} }},
                y1: {{ beginAtZero: true, position: 'right', grid: {{ drawOnChartArea: false }}, title: {{ display: true, text: 'Monto ($)' }} }},
                x: {{ ticks: {{ maxRotation: 45, minRotation: 20, font: {{ size: 10 }} }} }}
            }}
        }}
    }});

    // Top consumers
    const top = data.top_consumers.slice(0, 10);
    const topLabels = top.map(function(t) {{ return t.patente; }});
    const topLitros = top.map(function(t) {{ return t.total_litros; }});

    if (chartTop) chartTop.destroy();
    chartTop = new Chart(document.getElementById('chartTop').getContext('2d'), {{
        type: 'bar',
        data: {{
            labels: topLabels,
            datasets: [{{
                label: 'Litros',
                data: topLitros,
                backgroundColor: 'rgba(13,148,136,0.7)',
                borderRadius: 6
            }}]
        }},
        options: {{
            indexAxis: 'y',
            responsive: true,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
                x: {{ beginAtZero: true, title: {{ display: true, text: 'Litros' }} }}
            }}
        }}
    }});

    // Trend chart
    const trend = data.daily_trend;
    const trendLabels = trend.map(function(t) {{
        const p = t.fecha.split('-');
        return p[2] + '/' + p[1];
    }});
    const trendLitros = trend.map(function(t) {{ return t.litros; }});

    if (chartTrend) chartTrend.destroy();
    chartTrend = new Chart(document.getElementById('chartTrend').getContext('2d'), {{
        type: 'line',
        data: {{
            labels: trendLabels,
            datasets: [{{
                label: 'Litros',
                data: trendLitros,
                borderColor: '#0d9488',
                backgroundColor: 'rgba(13,148,136,0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 2,
                pointHoverRadius: 5
            }}]
        }},
        options: {{
            responsive: true,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
                y: {{ beginAtZero: true, title: {{ display: true, text: 'Litros' }} }},
                x: {{ ticks: {{ maxRotation: 45, font: {{ size: 10 }}, autoSkip: true, maxTicksLimit: 30 }} }}
            }}
        }}
    }});
}}

function populateDeptFilter(vehicles) {{
    const depts = {{}};
    vehicles.forEach(function(v) {{ if (v.departamento) depts[v.departamento] = true; }});
    const sel = document.getElementById('deptFilterSelect');
    const current = sel.value;
    sel.innerHTML = '<option value="">Todos los departamentos</option>';
    Object.keys(depts).sort().forEach(function(d) {{
        sel.innerHTML += '<option value="' + d + '"' + (d === current ? ' selected' : '') + '>' + d + '</option>';
    }});
}}

function renderAll(data, selectedMonth) {{
    currentFilteredData = data;
    renderKPIs(data.summary);

    const months = (reportData.months_available || []).slice().sort();
    if (selectedMonth && selectedMonth !== 'all') {{
        renderComparison(selectedMonth, data);
    }} else {{
        renderMonthlyOverview(months);
    }}

    renderCharts(data);
    populateDeptFilter(data.vehicles);
    renderVehicleTable(data.vehicles);
    renderDeptTable(data.departments);

    document.getElementById('jsonPreview').textContent = JSON.stringify(data.summary, null, 2);
}}

// ==================== MONTH FILTER ====================
function buildMonthFilter() {{
    const sel = document.getElementById('monthFilter');
    const months = (reportData.months_available || []).slice().sort();
    sel.innerHTML = '<option value="all">Todos los meses</option>';
    months.forEach(function(m) {{
        sel.innerHTML += '<option value="' + m + '">' + monthLabel(m) + '</option>';
    }});
}}

function onMonthChange() {{
    const sel = document.getElementById('monthFilter').value;
    if (sel === 'all') {{
        const data = computeFromTransactions(reportData.all_transactions);
        renderAll(data, 'all');
    }} else {{
        const data = computeMonthData(sel);
        renderAll(data, sel);
    }}
}}

// ==================== TABS ====================
function switchTab(name) {{
    document.querySelectorAll('.tab-btn').forEach(function(b) {{ b.classList.remove('active'); }});
    document.querySelectorAll('.tab-content').forEach(function(c) {{ c.classList.remove('active'); }});
    document.getElementById('tab-' + name).classList.add('active');
    document.querySelectorAll('.tab-btn').forEach(function(b) {{
        if (b.textContent.toLowerCase().indexOf(name.substring(0, 4)) >= 0 ||
            (name === 'vehicles' && b.textContent === 'Vehiculos') ||
            (name === 'departments' && b.textContent === 'Departamentos') ||
            (name === 'data' && b.textContent === 'Datos')) {{
            b.classList.add('active');
        }}
    }});
}}

// ==================== TABLE SORTING ====================
function sortTable(tableId, colIdx, type) {{
    const table = document.getElementById(tableId);
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const th = table.querySelectorAll('th')[colIdx];

    // Determine direction
    let asc = true;
    if (th.classList.contains('sorted-asc')) {{
        asc = false;
        th.classList.remove('sorted-asc');
        th.classList.add('sorted-desc');
    }} else {{
        table.querySelectorAll('th').forEach(function(h) {{ h.classList.remove('sorted-asc', 'sorted-desc'); }});
        th.classList.add('sorted-asc');
    }}

    rows.sort(function(a, b) {{
        let aVal = a.cells[colIdx].textContent.trim();
        let bVal = b.cells[colIdx].textContent.trim();
        if (type === 'num') {{
            aVal = parseNumericValue(aVal);
            bVal = parseNumericValue(bVal);
        }}
        if (aVal < bVal) return asc ? -1 : 1;
        if (aVal > bVal) return asc ? 1 : -1;
        return 0;
    }});

    rows.forEach(function(r) {{ tbody.appendChild(r); }});
}}

// ==================== CSV EXPORT ====================
function exportTableCSV(tableId, filename) {{
    const table = document.getElementById(tableId);
    const rows = Array.from(table.querySelectorAll('tr'));
    let csv = '';
    rows.forEach(function(row) {{
        const cells = Array.from(row.querySelectorAll('th, td'));
        csv += cells.map(function(c) {{
            let text = c.textContent.trim().replace(/"/g, '""');
            return '"' + text + '"';
        }}).join(',') + '\\n';
    }});
    downloadCSV(csv, filename + '.csv');
}}

function exportAllCSV() {{
    exportTableCSV('vehicleTable', 'vehiculos_' + new Date().toISOString().slice(0, 10));
}}

function downloadCSV(csv, filename) {{
    const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
}}

// ==================== WORKFLOW TRIGGER ====================
async function triggerWorkflow() {{
    const btn = document.getElementById('btnUpdate');
    const REPO = 'antoniocornejoa/copec-vehicle-report';
    const WORKFLOW = 'monthly_report.yml';
    let token = localStorage.getItem('gh_pat');
    if (!token) {{
        token = prompt('Para actualizar los datos, ingresa tu GitHub Personal Access Token.\\nSe guardara en tu navegador para futuras actualizaciones.\\n\\nToken (ghp_...):');
        if (!token || !token.startsWith('ghp_')) {{ alert('Token invalido. Debe comenzar con ghp_'); return; }}
        localStorage.setItem('gh_pat', token);
    }}
    btn.textContent = 'Actualizando...';
    btn.className = 'export-btn btn-update loading';
    try {{
        const res = await fetch('https://api.github.com/repos/' + REPO + '/actions/workflows/' + WORKFLOW + '/dispatches', {{
            method: 'POST',
            headers: {{
                'Authorization': 'token ' + token,
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            }},
            body: JSON.stringify({{ ref: 'main', inputs: {{ fetch_all_months: 'false' }} }})
        }});
        if (res.status === 204 || res.ok) {{
            btn.textContent = 'Actualizado!';
            btn.className = 'export-btn btn-update success';
            setTimeout(function() {{ btn.textContent = 'Actualizar Datos'; btn.className = 'export-btn btn-update'; }}, 4000);
        }} else if (res.status === 401 || res.status === 403) {{
            localStorage.removeItem('gh_pat');
            btn.textContent = 'Token invalido';
            btn.className = 'export-btn btn-update error';
            setTimeout(function() {{ btn.textContent = 'Actualizar Datos'; btn.className = 'export-btn btn-update'; }}, 3000);
        }} else {{
            throw new Error(res.status);
        }}
    }} catch (e) {{
        btn.textContent = 'Error';
        btn.className = 'export-btn btn-update error';
        setTimeout(function() {{ btn.textContent = 'Actualizar Datos'; btn.className = 'export-btn btn-update'; }}, 3000);
    }}
}}

// ==================== INIT ====================
document.addEventListener('DOMContentLoaded', function() {{
    // Set header subtitle
    const meta = reportData.summary || reportData.metadata || {{}};
    document.getElementById('headerSubtitle').textContent =
        'Periodo: ' + (meta.periodo || '') + ' | Generado: ' + (meta.fecha_generacion || '');

    buildMonthFilter();

    // Initial render with all data
    const allData = computeFromTransactions(reportData.all_transactions);
    renderAll(allData, 'all');
}});
</script>
</body>
</html>"""
    return html


def main():
    """Main entry point."""
    data_dir = os.environ.get("DATA_DIR", "data")
    output_dir = os.environ.get("OUTPUT_DIR", "docs")

    json_path = os.path.join(data_dir, "report_data.json")

    if not os.path.exists(json_path):
        print(f"Error: No se encontro el archivo de datos: {json_path}")
        sys.exit(1)

    print(f"Leyendo datos desde: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        report_data = json.load(f)

    print("Generando HTML...")
    html = generate_html(report_data)

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "index.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Informe generado exitosamente: {output_path}")
    print(f"  - Transacciones: {len(report_data.get('all_transactions', []))}")
    print(f"  - Meses: {', '.join(report_data.get('months_available', []))}")
    print(f"  - Vehiculos: {len(report_data.get('vehicles', {}))}")


if __name__ == "__main__":
    main()
