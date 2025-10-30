#!/usr/bin/env python3
"""
Script para generar reporte de performance a partir de métricas.
Lee el JSON generado por analyze_logs.py y crea un reporte legible.
"""
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path


def parse_args():
    """Parse argumentos"""
    parser = argparse.ArgumentParser(
        description='Genera reporte de performance desde métricas JSON'
    )
    parser.add_argument(
        'metrics_file',
        type=str,
        help='Path al archivo JSON de métricas'
    )
    parser.add_argument(
        '--format',
        '-f',
        choices=['markdown', 'html', 'text'],
        default='markdown',
        help='Formato de salida'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        default=None,
        help='Archivo de salida (stdout si no se especifica)'
    )
    
    return parser.parse_args()


def load_metrics(filepath: str) -> dict:
    """Carga métricas desde archivo JSON"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Archivo no encontrado: {filepath}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: JSON inválido: {e}", file=sys.stderr)
        sys.exit(1)


def generate_markdown_report(data: dict) -> str:
    """Genera reporte en formato Markdown"""
    metrics = data['metrics']
    timestamp = data.get('timestamp', datetime.utcnow().isoformat())
    
    # Emojis para visualización
    hit_emoji = '✅' if metrics['hit_ratio'] >= 0.8 else ('⚠️' if metrics['hit_ratio'] >= 0.6 else '❌')
    latency_emoji = '✅' if metrics['p95_latency_ms'] < 200 else ('⚠️' if metrics['p95_latency_ms'] < 500 else '❌')
    error_emoji = '✅' if metrics['error_rate'] < 0.01 else ('⚠️' if metrics['error_rate'] < 0.05 else '❌')
    
    report = f"""# 📊 Performance Report

**Generado**: {timestamp}  
**Archivo de logs**: {data.get('log_file', 'N/A')}

---

## 🎯 Métricas Principales

### Cache Performance {hit_emoji}

| Métrica | Valor | Estado |
|---------|-------|--------|
| **Hit Ratio** | {metrics['hit_ratio']*100:.2f}% | {'✅ Excelente' if metrics['hit_ratio'] >= 0.8 else '⚠️ Mejorable' if metrics['hit_ratio'] >= 0.6 else '❌ Crítico'} |
| Total Requests | {metrics['total_requests']:,} | - |
| Cache Hits | {metrics['cache_hits']:,} | - |
| Cache Misses | {metrics['cache_misses']:,} | - |
| Cache Bypass | {metrics['cache_bypass']:,} | - |

**Objetivo**: Hit Ratio ≥ 80%  
**Actual**: {metrics['hit_ratio']*100:.2f}%  
**Estado**: {'✅ CUMPLE' if metrics['hit_ratio'] >= 0.8 else '❌ NO CUMPLE'}

---

### Latencia {latency_emoji}

| Percentil | Latencia | Objetivo | Estado |
|-----------|----------|----------|--------|
| **P50** | {metrics['p50_latency_ms']:.2f}ms | < 100ms | {'✅' if metrics['p50_latency_ms'] < 100 else '⚠️'} |
| **P95** | {metrics['p95_latency_ms']:.2f}ms | < 200ms | {'✅' if metrics['p95_latency_ms'] < 200 else '⚠️'} |
| **P99** | {metrics['p99_latency_ms']:.2f}ms | < 500ms | {'✅' if metrics['p99_latency_ms'] < 500 else '⚠️'} |

**Objetivo**: P95 < 200ms  
**Actual**: {metrics['p95_latency_ms']:.2f}ms  
**Estado**: {'✅ CUMPLE' if metrics['p95_latency_ms'] < 200 else '❌ NO CUMPLE'}

---

### Confiabilidad {error_emoji}

| Métrica | Valor | Objetivo | Estado |
|---------|-------|----------|--------|
| **Error Rate** | {metrics['error_rate']*100:.2f}% | < 1% | {'✅' if metrics['error_rate'] < 0.01 else '⚠️'} |
| Total Bytes | {metrics['total_bytes'] / (1024*1024):.2f} MB | - | - |

---

## 📈 Distribución de Status Codes

| Code | Count | Percentage |
|------|-------|------------|
"""
    
    # Agregar status codes
    total_requests = metrics['total_requests']
    for code, count in sorted(metrics['status_codes'].items()):
        percentage = (int(count) / total_requests * 100) if total_requests > 0 else 0
        report += f"| {code} | {count:,} | {percentage:.2f}% |\n"
    
    report += f"""
---

## 🎯 Resumen de Cumplimiento

| Criterio | Objetivo | Actual | Cumple |
|----------|----------|--------|--------|
| Hit Ratio | ≥ 80% | {metrics['hit_ratio']*100:.2f}% | {'✅' if metrics['hit_ratio'] >= 0.8 else '❌'} |
| P95 Latency | < 200ms | {metrics['p95_latency_ms']:.2f}ms | {'✅' if metrics['p95_latency_ms'] < 200 else '❌'} |
| Error Rate | < 1% | {metrics['error_rate']*100:.2f}% | {'✅' if metrics['error_rate'] < 0.01 else '❌'} |

---

## 💡 Recomendaciones

"""
    
    # Agregar recomendaciones basadas en métricas
    recommendations = []
    
    if metrics['hit_ratio'] < 0.8:
        recommendations.append("- 🔴 **Hit ratio bajo**: Revisar políticas de caché y Cache-Control headers")
        recommendations.append("  - Verificar que los endpoints cacheables tengan max-age > 0")
        recommendations.append("  - Analizar patrones de acceso para optimizar TTLs")
    
    if metrics['p95_latency_ms'] > 200:
        recommendations.append("- 🔴 **Latencia alta**: Optimizar performance del backend")
        recommendations.append("  - Revisar queries lentas")
        recommendations.append("  - Considerar warming del caché")
    
    if metrics['error_rate'] > 0.01:
        recommendations.append("- 🔴 **Tasa de error elevada**: Investigar errores 5xx")
        recommendations.append("  - Revisar logs del backend")
        recommendations.append("  - Verificar health checks")
    
    if not recommendations:
        recommendations.append("- ✅ **Todo en orden**: Métricas dentro de los objetivos")
    
    report += '\n'.join(recommendations)
    
    report += f"""

---

## 📊 Gráfico de Performance

```
Cache Hit Ratio: {'█' * int(metrics['hit_ratio'] * 20)}{'░' * (20 - int(metrics['hit_ratio'] * 20))} {metrics['hit_ratio']*100:.1f}%
P95 Latency:     {'█' * min(20, int(metrics['p95_latency_ms'] / 10))}{'░' * max(0, 20 - int(metrics['p95_latency_ms'] / 10))} {metrics['p95_latency_ms']:.0f}ms
Error Rate:      {'█' * int(metrics['error_rate'] * 2000)}{'░' * (20 - int(metrics['error_rate'] * 2000))} {metrics['error_rate']*100:.2f}%
```

---

*Reporte generado automáticamente por `generate_report.py`*
"""
    
    return report


def generate_text_report(data: dict) -> str:
    """Genera reporte en formato texto plano"""
    metrics = data['metrics']
    
    report = f"""
PERFORMANCE REPORT
==================
Generated: {data.get('timestamp', 'N/A')}
Log file: {data.get('log_file', 'N/A')}

CACHE METRICS
-------------
Total Requests:  {metrics['total_requests']:,}
Cache Hits:      {metrics['cache_hits']:,} ({metrics['hit_ratio']*100:.2f}%)
Cache Misses:    {metrics['cache_misses']:,}
Cache Bypass:    {metrics['cache_bypass']:,}

LATENCY
-------
P50: {metrics['p50_latency_ms']:.2f}ms
P95: {metrics['p95_latency_ms']:.2f}ms
P99: {metrics['p99_latency_ms']:.2f}ms

RELIABILITY
-----------
Error Rate:      {metrics['error_rate']*100:.2f}%
Total Bytes:     {metrics['total_bytes'] / (1024*1024):.2f} MB

STATUS CODES
------------
"""
    
    for code, count in sorted(metrics['status_codes'].items()):
        report += f"{code}: {count:,}\n"
    
    report += f"""
COMPLIANCE
----------
Hit Ratio ≥ 80%: {'PASS' if metrics['hit_ratio'] >= 0.8 else 'FAIL'}
P95 < 200ms:     {'PASS' if metrics['p95_latency_ms'] < 200 else 'FAIL'}
Error Rate < 1%: {'PASS' if metrics['error_rate'] < 0.01 else 'FAIL'}
"""
    
    return report


def generate_html_report(data: dict) -> str:
    """Genera reporte en formato HTML"""
    metrics = data['metrics']
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Performance Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .metric-label {{
            color: #666;
            margin-top: 5px;
        }}
        .status-good {{ color: #22c55e; }}
        .status-warning {{ color: #f59e0b; }}
        .status-bad {{ color: #ef4444; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #667eea;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Performance Report</h1>
        <p>Generated: {data.get('timestamp', 'N/A')}</p>
    </div>
    
    <div class="metric-card">
        <h2>Cache Performance</h2>
        <div class="metric-value {'status-good' if metrics['hit_ratio'] >= 0.8 else 'status-bad'}">
            {metrics['hit_ratio']*100:.2f}%
        </div>
        <div class="metric-label">Hit Ratio (Target: ≥80%)</div>
        <p>
            Total Requests: {metrics['total_requests']:,}<br>
            Cache Hits: {metrics['cache_hits']:,}<br>
            Cache Misses: {metrics['cache_misses']:,}
        </p>
    </div>
    
    <div class="metric-card">
        <h2>Latency</h2>
        <table>
            <tr>
                <th>Percentile</th>
                <th>Value</th>
                <th>Target</th>
                <th>Status</th>
            </tr>
            <tr>
                <td>P50</td>
                <td>{metrics['p50_latency_ms']:.2f}ms</td>
                <td>&lt; 100ms</td>
                <td class="{'status-good' if metrics['p50_latency_ms'] < 100 else 'status-warning'}">
                    {'✅' if metrics['p50_latency_ms'] < 100 else '⚠️'}
                </td>
            </tr>
            <tr>
                <td>P95</td>
                <td>{metrics['p95_latency_ms']:.2f}ms</td>
                <td>&lt; 200ms</td>
                <td class="{'status-good' if metrics['p95_latency_ms'] < 200 else 'status-warning'}">
                    {'✅' if metrics['p95_latency_ms'] < 200 else '⚠️'}
                </td>
            </tr>
            <tr>
                <td>P99</td>
                <td>{metrics['p99_latency_ms']:.2f}ms</td>
                <td>&lt; 500ms</td>
                <td class="{'status-good' if metrics['p99_latency_ms'] < 500 else 'status-warning'}">
                    {'✅' if metrics['p99_latency_ms'] < 500 else '⚠️'}
                </td>
            </tr>
        </table>
    </div>
    
    <div class="metric-card">
        <h2>Status Codes</h2>
        <table>
            <tr>
                <th>Code</th>
                <th>Count</th>
                <th>Percentage</th>
            </tr>
"""
    
    total = metrics['total_requests']
    for code, count in sorted(metrics['status_codes'].items()):
        pct = (int(count) / total * 100) if total > 0 else 0
        html += f"""
            <tr>
                <td>{code}</td>
                <td>{count:,}</td>
                <td>{pct:.2f}%</td>
            </tr>
"""
    
    html += """
        </table>
    </div>
</body>
</html>
"""
    
    return html


def main():
    """Función principal"""
    args = parse_args()
    
    # Cargar métricas
    data = load_metrics(args.metrics_file)
    
    # Generar reporte según formato
    if args.format == 'markdown':
        report = generate_markdown_report(data)
    elif args.format == 'html':
        report = generate_html_report(data)
    else:  # text
        report = generate_text_report(data)
    
    # Escribir salida
    if args.output:
        Path(args.output).write_text(report)
        print(f"✓ Reporte generado: {args.output}", file=sys.stderr)
    else:
        print(report)
    
    sys.exit(0)


if __name__ == '__main__':
    main()