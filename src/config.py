"""
Configuración 12-Factor: toda la config viene de variables de entorno.
Implementa patrón Facade para acceso centralizado a configuración.
"""
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class AppConfig:
    """Configuración de la aplicación"""
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False
    version: str = "1.0.0"
    log_level: str = "INFO"

@dataclass
class NginxConfig:
    """Configuración del proxy Nginx"""
    host: str = "0.0.0.0"
    port: int = 80
    cache_path: str = "/var/cache/nginx"
    cache_size: str = "100m"
    cache_max_size: str = "1g"
    cache_inactive: str = "60m"

@dataclass
class MetricsConfig:
    """Configuración de métricas"""
    enabled: bool = True
    log_file: str = "/var/log/nginx/access.log"
    metrics_port: int = 9090
    scrape_interval: int = 60

class ConfigFacade:
    """
    Facade para acceso unificado a toda la configuración.
    Implementa 12-Factor: configuración por variables de entorno.
    """
    
    def __init__(self):
        self._app: Optional[AppConfig] = None
        self._nginx: Optional[NginxConfig] = None
        self._metrics: Optional[MetricsConfig] = None
    
    @property
    def app(self) -> AppConfig:
        """Configuración de la aplicación"""
        if self._app is None:
            self._app = AppConfig(
                host=os.getenv('BACKEND_HOST', '0.0.0.0'),
                port=int(os.getenv('BACKEND_PORT', '8080')),
                debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true',
                version=os.getenv('APP_VERSION', '1.0.0'),
                log_level=os.getenv('LOG_LEVEL', 'INFO'),
            )
        return self._app
    
    @property
    def nginx(self) -> NginxConfig:
        """Configuración del proxy"""
        if self._nginx is None:
            self._nginx = NginxConfig(
                host=os.getenv('NGINX_HOST', '0.0.0.0'),
                port=int(os.getenv('NGINX_PORT', '80')),
                cache_path=os.getenv('NGINX_CACHE_PATH', '/var/cache/nginx'),
                cache_size=os.getenv('NGINX_CACHE_SIZE', '100m'),
                cache_max_size=os.getenv('NGINX_CACHE_MAX_SIZE', '1g'),
                cache_inactive=os.getenv('NGINX_CACHE_INACTIVE', '60m'),
            )
        return self._nginx
    
    @property
    def metrics(self) -> MetricsConfig:
        """Configuración de métricas"""
        if self._metrics is None:
            self._metrics = MetricsConfig(
                enabled=os.getenv('METRICS_ENABLED', 'true').lower() == 'true',
                log_file=os.getenv('NGINX_LOG_FILE', '/var/log/nginx/access.log'),
                metrics_port=int(os.getenv('METRICS_PORT', '9090')),
                scrape_interval=int(os.getenv('METRICS_SCRAPE_INTERVAL', '60')),
            )
        return self._metrics
    
    def to_dict(self) -> Dict[str, Any]:
        """Exporta toda la configuración como diccionario"""
        return {
            'app': {
                'host': self.app.host,
                'port': self.app.port,
                'debug': self.app.debug,
                'version': self.app.version,
                'log_level': self.app.log_level,
            },
            'nginx': {
                'host': self.nginx.host,
                'port': self.nginx.port,
                'cache_path': self.nginx.cache_path,
                'cache_size': self.nginx.cache_size,
                'cache_max_size': self.nginx.cache_max_size,
                'cache_inactive': self.nginx.cache_inactive,
            },
            'metrics': {
                'enabled': self.metrics.enabled,
                'log_file': self.metrics.log_file,
                'metrics_port': self.metrics.metrics_port,
                'scrape_interval': self.metrics.scrape_interval,
            }
        }
    
    def validate(self) -> bool:
        """Valida que la configuración sea válida"""
        errors = []
        
        # Validar puertos
        if not (1 <= self.app.port <= 65535):
            errors.append(f"Invalid app port: {self.app.port}")
        
        if not (1 <= self.nginx.port <= 65535):
            errors.append(f"Invalid nginx port: {self.nginx.port}")
        
        if not (1 <= self.metrics.metrics_port <= 65535):
            errors.append(f"Invalid metrics port: {self.metrics.metrics_port}")
        
        # Validar log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.app.log_level.upper() not in valid_levels:
            errors.append(f"Invalid log level: {self.app.log_level}")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True

# Instancia global del facade (singleton)
config = ConfigFacade()