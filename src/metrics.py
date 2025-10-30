"""
Módulo para procesar logs de Nginx y calcular métricas de caché
"""
import re
from dataclasses import dataclass, asdict
from typing import List, Optional
import statistics


@dataclass
class CacheMetrics:
    """Métricas de caché"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_bypass: int = 0
    cache_stale: int = 0
    cache_updating: int = 0
    cache_revalidated: int = 0
    
    error_5xx: int = 0
    error_4xx: int = 0
    
    total_bytes: int = 0
    latencies: List[float] = None
    
    def __post_init__(self):
        if self.latencies is None:
            self.latencies = []
    
    @property
    def hit_ratio(self) -> float:
        """Calcula el hit ratio (hits / (hits + misses))"""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total
    
    @property
    def error_rate(self) -> float:
        """Calcula el error rate (errores / total)"""
        if self.total_requests == 0:
            return 0.0
        return (self.error_5xx + self.error_4xx) / self.total_requests
    
    @property
    def p50_latency(self) -> float:
        """Latencia P50 en segundos"""
        if not self.latencies:
            return 0.0
        return statistics.median(self.latencies)
    
    @property
    def p95_latency(self) -> float:
        """Latencia P95 en segundos"""
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[idx] if idx < len(sorted_lat) else sorted_lat[-1]
    
    @property
    def p99_latency(self) -> float:
        """Latencia P99 en segundos"""
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.99)
        return sorted_lat[idx] if idx < len(sorted_lat) else sorted_lat[-1]
    
    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización"""
        data = asdict(self)
        # No incluir lista completa de latencias
        data['latencies'] = len(self.latencies)
        # Agregar métricas calculadas
        data['hit_ratio'] = self.hit_ratio
        data['error_rate'] = self.error_rate
        data['p50_latency'] = self.p50_latency
        data['p95_latency'] = self.p95_latency
        data['p99_latency'] = self.p99_latency
        return data


class MetricsAnalyzer:
    """Analizador de logs de Nginx"""
    
    # Formato del log: $remote_addr - [$time_local] "$request" $status $body_bytes_sent $request_time "$upstream_cache_status"
    LOG_PATTERN = re.compile(
        r'^(?P<ip>[\d.]+) - \[(?P<time>[^\]]+)\] '
        r'"(?P<method>\w+) (?P<path>[^\s]+) (?P<protocol>[^"]+)" '
        r'(?P<status>\d+) (?P<bytes>\d+) (?P<latency>[\d.]+) '
        r'"(?P<cache_status>[^"]*)"'
    )
    
    def __init__(self):
        self.metrics = CacheMetrics()
    
    def parse_line(self, line: str) -> Optional[dict]:
        """
        Parsea una línea del log
        
        Args:
            line: Línea del log
            
        Returns:
            Diccionario con los campos parseados o None si no coincide
        """
        match = self.LOG_PATTERN.match(line.strip())
        if not match:
            return None
        return match.groupdict()
    
    def process_log_line(self, line: str):
        """Procesa una línea del log y actualiza métricas"""
        parsed = self.parse_line(line)
        if not parsed:
            return
        
        # Incrementar total
        self.metrics.total_requests += 1
        
        # Cache status
        cache_status = parsed['cache_status'].strip()
        if cache_status == 'HIT':
            self.metrics.cache_hits += 1
        elif cache_status == 'MISS':
            self.metrics.cache_misses += 1
        elif cache_status == 'BYPASS':
            self.metrics.cache_bypass += 1
        elif cache_status == 'STALE':
            self.metrics.cache_stale += 1
        elif cache_status == 'UPDATING':
            self.metrics.cache_updating += 1
        elif cache_status == 'REVALIDATED':
            self.metrics.cache_revalidated += 1
        
        # Status codes
        status = int(parsed['status'])
        if 500 <= status < 600:
            self.metrics.error_5xx += 1
        elif 400 <= status < 500:
            self.metrics.error_4xx += 1
        
        # Bytes
        self.metrics.total_bytes += int(parsed['bytes'])
        
        # Latency
        try:
            latency = float(parsed['latency'])
            self.metrics.latencies.append(latency)
        except (ValueError, KeyError):
            pass
    
    def process_log_content(self, content: str) -> CacheMetrics:
        """
        Procesa el contenido de un log completo
        
        Args:
            content: Contenido del archivo de log
            
        Returns:
            Objeto CacheMetrics con las métricas calculadas
        """
        self.metrics = CacheMetrics()
        
        for line in content.splitlines():
            if line.strip():
                self.process_log_line(line)
        
        return self.metrics
    
    def process_log_file(self, filepath: str) -> CacheMetrics:
        """
        Procesa un archivo de log
        
        Args:
            filepath: Path al archivo de log
            
        Returns:
            Objeto CacheMetrics con las métricas calculadas
        """
        with open(filepath, 'r') as f:
            content = f.read()
        return self.process_log_content(content)
    
    def get_metrics_summary(self) -> str:
        """Retorna un resumen de las métricas en texto"""
        m = self.metrics
        return f"""
Cache Metrics Summary
=====================
Total Requests: {m.total_requests}
Cache Hits:     {m.cache_hits} ({m.hit_ratio*100:.2f}%)
Cache Misses:   {m.cache_misses}
Cache Bypass:   {m.cache_bypass}
Cache Stale:    {m.cache_stale}
Cache Updating: {m.cache_updating}

Error Rate: {m.error_rate*100:.2f}%
  4xx errors: {m.error_4xx}
  5xx errors: {m.error_5xx}

Latency:
  P50: {m.p50_latency*1000:.2f}ms
  P95: {m.p95_latency*1000:.2f}ms
  P99: {m.p99_latency*1000:.2f}ms

Total Bytes: {m.total_bytes / (1024*1024):.2f} MB
"""