#!/usr/bin/env python3
"""
Script para analizar logs de Nginx desde un contenedor Docker.
Se ejecuta en el HOST y lee logs del contenedor usando docker exec.

Uso:
    python3 scripts/analyze_logs.py /var/log/nginx/access.log --container edge-cache-proxy
    python3 scripts/analyze_logs.py --container edge-cache-proxy  # usa path default
"""
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

# Agregar src al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.metrics import MetricsAnalyzer


def parse_args():
    """Parse argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description='Analiza logs de Nginx desde un contenedor Docker'
    )
    parser.add_argument(
        'log_file',
        type=str,
        nargs='?',
        default='stdout',
        help='Path al archivo de log DENTRO del contenedor, o "stdout"/"docker" para docker logs (default: stdout)'
    )
    parser.add_argument(
        '--container',
        '-c',
        type=str,
        required=True,
        help='Nombre o ID del contenedor Docker'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        default=None,
        help='Path al archivo de salida (JSON). Si no se especifica, imprime a stdout'
    )
    parser.add_argument(
        '--format',
        '-f',
        choices=['json', 'text', 'summary', 'prometheus'],
        default='summary',
        help='Formato de salida'
    )
    parser.add_argument(
        '--min-hit-ratio',
        type=float,
        default=0.8,
        help='Hit ratio mínimo esperado (para alertas)'
    )
    parser.add_argument(
        '--watch',
        '-w',
        action='store_true',
        help='Modo watch: analiza logs continuamente cada N segundos'
    )
    parser.add_argument(
        '--interval',
        '-i',
        type=int,
        default=30,
        help='Intervalo en segundos para modo watch (default: 30)'
    )
    parser.add_argument(
        '--tail',
        '-t',
        type=int,
        default=None,
        help='Solo analizar las últimas N líneas del log'
    )
    
    return parser.parse_args()


def read_log_from_container(container: str, log_path: str, tail: Optional[int] = None) -> str:
    """
    Lee el contenido del log desde el contenedor.
    Si log_path es 'stdout' o 'docker', usa docker logs, sino usa docker exec cat
    
    Args:
        container: Nombre o ID del contenedor
        log_path: Path del archivo dentro del contenedor o 'stdout'/'docker' para docker logs
        tail: Si se especifica, solo lee las últimas N líneas
        
    Returns:
        Contenido del archivo como string
        
    Raises:
        subprocess.CalledProcessError: Si el comando docker falla
    """
    # Si pide 'stdout' o 'docker', usar docker logs
    if log_path.lower() in ['stdout', 'docker']:
        if tail:
            cmd = ['docker', 'logs', '--tail', str(tail), container]
        else:
            cmd = ['docker', 'logs', container]
    else:
        # Leer desde archivo dentro del contenedor
        if tail:
            cmd = ['docker', 'exec', container, 'tail', '-n', str(tail), log_path]
        else:
            cmd = ['docker', 'exec', container, 'cat', log_path]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error al leer logs del contenedor: {e.stderr}", file=sys.stderr)
        raise


def verify_container_exists(container: str) -> bool:
    """Verifica que el contenedor existe y está corriendo"""
    try:
        result = subprocess.run(
            ['docker', 'inspect', '-f', '{{.State.Running}}', container],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip() == 'true'
    except subprocess.CalledProcessError:
        return False


def format_prometheus_metrics(metrics):
    """Formatea métricas en formato Prometheus"""
    timestamp = int(datetime.now().timestamp() * 1000)
    return f"""# HELP nginx_cache_hit_ratio Cache hit ratio
# TYPE nginx_cache_hit_ratio gauge
nginx_cache_hit_ratio {metrics.hit_ratio} {timestamp}

# HELP nginx_cache_hits_total Total cache hits
# TYPE nginx_cache_hits_total counter
nginx_cache_hits_total {metrics.cache_hits} {timestamp}

# HELP nginx_cache_misses_total Total cache misses
# TYPE nginx_cache_misses_total counter
nginx_cache_misses_total {metrics.cache_misses} {timestamp}

# HELP nginx_requests_total Total requests
# TYPE nginx_requests_total counter
nginx_requests_total {metrics.total_requests} {timestamp}

# HELP nginx_latency_p50_seconds P50 latency
# TYPE nginx_latency_p50_seconds gauge
nginx_latency_p50_seconds {metrics.p50_latency} {timestamp}

# HELP nginx_latency_p95_seconds P95 latency
# TYPE nginx_latency_p95_seconds gauge
nginx_latency_p95_seconds {metrics.p95_latency} {timestamp}

# HELP nginx_latency_p99_seconds P99 latency
# TYPE nginx_latency_p99_seconds gauge
nginx_latency_p99_seconds {metrics.p99_latency} {timestamp}

# HELP nginx_error_rate Error rate
# TYPE nginx_error_rate gauge
nginx_error_rate {metrics.error_rate} {timestamp}
"""


def analyze_once(args):
    """Analiza los logs una vez"""
    print(f"[DEBUG] Verificando contenedor '{args.container}'...", file=sys.stderr)
    
    # Verificar que el contenedor existe
    if not verify_container_exists(args.container):
        print(f"Error: Contenedor '{args.container}' no existe o no está corriendo", file=sys.stderr)
        return False
    
    print(f"[DEBUG] Contenedor encontrado y corriendo", file=sys.stderr)
    
    # Leer logs del contenedor
    log_source = "docker logs" if args.log_file.lower() in ['stdout', 'docker'] else args.log_file
    print(f"[DEBUG] Leyendo logs de {args.container} ({log_source})...", file=sys.stderr)
    
    import time
    start_time = time.time()
    
    try:
        log_content = read_log_from_container(args.container, args.log_file, args.tail)
        read_time = time.time() - start_time
        print(f"[DEBUG] Logs leídos en {read_time:.2f}s ({len(log_content)} bytes)", file=sys.stderr)
    except Exception as e:
        print(f"Error al leer logs: {e}", file=sys.stderr)
        return False
    
    if not log_content.strip():
        print("Advertencia: El archivo de log está vacío", file=sys.stderr)
        return False
    
    # Analizar logs
    num_lines = len(log_content.splitlines())
    print(f"Analizando {num_lines:,} líneas...", file=sys.stderr)
    
    analyzer = MetricsAnalyzer()
    
    try:
        start_time = time.time()
        metrics = analyzer.process_log_content(log_content)
        process_time = time.time() - start_time
        print(f"✓ Análisis completado en {process_time:.2f}s", file=sys.stderr)
    except Exception as e:
        print(f"Error al procesar logs: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False
    
    # Generar salida según formato
    if args.format == 'json':
        output = json.dumps({
            'timestamp': datetime.utcnow().isoformat(),
            'container': args.container,
            'log_file': args.log_file,
            'metrics': metrics.to_dict()
        }, indent=2)
    
    elif args.format == 'prometheus':
        output = format_prometheus_metrics(metrics)
    
    elif args.format == 'text':
        output = analyzer.get_metrics_summary()
    
    else:  # summary
        output = f"""
Métricas de Caché - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}
Contenedor: {args.container}
Log: {args.log_file}

Total Requests:  {metrics.total_requests}
Cache Hits:      {metrics.cache_hits} ({metrics.hit_ratio*100:.2f}%)
Cache Misses:    {metrics.cache_misses}
Cache Bypass:    {metrics.cache_bypass}

Latencia:
  P50: {metrics.p50_latency*1000:.2f}ms
  P95: {metrics.p95_latency*1000:.2f}ms
  P99: {metrics.p99_latency*1000:.2f}ms

Error Rate:      {metrics.error_rate*100:.2f}%
Total Bytes:     {metrics.total_bytes / (1024*1024):.2f} MB
"""
    
    # Escribir salida
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output)
        print(f"Métricas guardadas en: {args.output}", file=sys.stderr)
    else:
        print(output)
    
    # Verificar alertas
    if metrics.hit_ratio < args.min_hit_ratio:
        print(
            f"\n⚠️  ALERTA: Hit ratio ({metrics.hit_ratio*100:.2f}%) "
            f"está por debajo del mínimo ({args.min_hit_ratio*100:.2f}%)",
            file=sys.stderr
        )
        return False
    
    print("\n✓ Análisis completado", file=sys.stderr)
    return True


def main():
    """Función principal"""
    args = parse_args()
    
    if args.watch:
        # Modo watch: analiza continuamente
        import time
        print(f"Modo watch activado. Analizando cada {args.interval}s...", file=sys.stderr)
        print("Presiona Ctrl+C para detener\n", file=sys.stderr)
        
        try:
            while True:
                analyze_once(args)
                print(f"\nEsperando {args.interval}s...\n", file=sys.stderr)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n\n✓ Análisis detenido", file=sys.stderr)
            sys.exit(0)
    else:
        # Análisis único
        success = analyze_once(args)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()