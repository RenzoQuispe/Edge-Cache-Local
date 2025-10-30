"""
Edge Cache Local - Backend Service

Microservicio de caché con Nginx reverse proxy.

Componentes principales:
- app: Backend Flask con políticas de caché
- config: Configuración 12-Factor
- metrics: Análisis de métricas de logs
"""

__version__ = "1.0.0"
__author__ = "Edge Cache Team"

# Imports principales
from src.app import create_app, CachePolicy, CacheConfig
from src.config import config, ConfigFacade
from src.metrics import MetricsAnalyzer, CacheMetrics

__all__ = [
    "create_app",
    "CachePolicy",
    "CacheConfig",
    "config",
    "ConfigFacade",
    "MetricsAnalyzer",
    "CacheMetrics",
    'MetricsAnalyzer',
    'CacheMetrics',
]