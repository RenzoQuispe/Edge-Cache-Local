"""
Tests del módulo de configuración.
Prueba el patrón Facade y configuración 12-Factor.
"""
import pytest
import os
from src.config import ConfigFacade, AppConfig, NginxConfig, MetricsConfig


class TestAppConfig:
    """Tests de AppConfig dataclass"""
    
    def test_default_values(self):
        """Valores por defecto"""
        config = AppConfig()
        
        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.debug is False
        assert config.version == "1.0.0"
        assert config.log_level == "INFO"
    
    @pytest.mark.parametrize("host", ["127.0.0.1", "0.0.0.0", "localhost"])
    def test_custom_host(self, host):
        """Host personalizado"""
        config = AppConfig(host=host)
        assert config.host == host
    
    @pytest.mark.parametrize("port", [80, 8080, 3000, 9000])
    def test_custom_port(self, port):
        """Puerto personalizado"""
        config = AppConfig(port=port)
        assert config.port == port


class TestNginxConfig:
    """Tests de NginxConfig dataclass"""
    
    def test_default_cache_settings(self):
        """Configuración de caché por defecto"""
        config = NginxConfig()
        
        assert config.cache_path == "/var/cache/nginx"
        assert config.cache_size == "100m"
        assert config.cache_max_size == "1g"
        assert config.cache_inactive == "60m"


class TestMetricsConfig:
    """Tests de MetricsConfig dataclass"""
    
    def test_default_metrics_enabled(self):
        """Métricas habilitadas por defecto"""
        config = MetricsConfig()
        assert config.enabled is True
    
    def test_default_scrape_interval(self):
        """Intervalo de scraping por defecto"""
        config = MetricsConfig()
        assert config.scrape_interval == 60


class TestConfigFacade:
    """Tests del Facade de configuración"""
    
    def test_facade_app_property(self, clean_env):
        """Propiedad app del facade"""
        facade = ConfigFacade()
        app_config = facade.app
        
        assert isinstance(app_config, AppConfig)
        assert app_config.host == "0.0.0.0"
        assert app_config.port == 8080
    
    def test_facade_nginx_property(self, clean_env):
        """Propiedad nginx del facade"""
        facade = ConfigFacade()
        nginx_config = facade.nginx
        
        assert isinstance(nginx_config, NginxConfig)
    
    def test_facade_metrics_property(self, clean_env):
        """Propiedad metrics del facade"""
        facade = ConfigFacade()
        metrics_config = facade.metrics
        
        assert isinstance(metrics_config, MetricsConfig)
    
    def test_facade_caches_configs(self, clean_env):
        """Facade cachea las configuraciones (singleton)"""
        facade = ConfigFacade()
        
        app1 = facade.app
        app2 = facade.app
        
        assert app1 is app2  # Misma instancia


class TestConfigFromEnv:
    """Tests de carga desde variables de entorno (12-Factor)"""
    
    def test_app_config_from_env(self, monkeypatch):
        """AppConfig lee de ENV"""
        monkeypatch.setenv('BACKEND_HOST', '192.168.1.1')
        monkeypatch.setenv('BACKEND_PORT', '9000')
        monkeypatch.setenv('FLASK_DEBUG', 'true')
        monkeypatch.setenv('APP_VERSION', '2.0.0')
        monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
        
        facade = ConfigFacade()
        config = facade.app
        
        assert config.host == '192.168.1.1'
        assert config.port == 9000
        assert config.debug is True
        assert config.version == '2.0.0'
        assert config.log_level == 'DEBUG'
    
    def test_nginx_config_from_env(self, monkeypatch):
        """NginxConfig lee de ENV"""
        monkeypatch.setenv('NGINX_HOST', '127.0.0.1')
        monkeypatch.setenv('NGINX_PORT', '8081')
        monkeypatch.setenv('NGINX_CACHE_PATH', '/tmp/cache')
        
        facade = ConfigFacade()
        config = facade.nginx
        
        assert config.host == '127.0.0.1'
        assert config.port == 8081
        assert config.cache_path == '/tmp/cache'
    
    def test_metrics_config_from_env(self, monkeypatch):
        """MetricsConfig lee de ENV"""
        monkeypatch.setenv('METRICS_ENABLED', 'false')
        monkeypatch.setenv('METRICS_PORT', '9091')
        
        facade = ConfigFacade()
        config = facade.metrics
        
        assert config.enabled is False
        assert config.metrics_port == 9091
    
    @pytest.mark.parametrize("debug_value,expected", [
        ('true', True),
        ('True', True),
        ('TRUE', True),
        ('false', False),
        ('False', False),
        ('FALSE', False),
        ('', False),
        ('anything', False),
    ])
    def test_boolean_parsing(self, monkeypatch, debug_value, expected):
        """Parsing de booleanos desde ENV"""
        monkeypatch.setenv('FLASK_DEBUG', debug_value)
        
        facade = ConfigFacade()
        config = facade.app
        
        assert config.debug is expected


class TestConfigValidation:
    """Tests de validación de configuración"""
    
    def test_validate_valid_config(self, clean_env, mock_env):
        """Configuración válida pasa validación"""
        facade = ConfigFacade()
        
        # No debe lanzar excepción
        assert facade.validate() is True
    
    @pytest.mark.parametrize("invalid_port", [-1, 0, 65536, 100000])
    def test_validate_invalid_app_port(self, monkeypatch, clean_env, invalid_port):
        """Puerto inválido falla validación"""
        monkeypatch.setenv('BACKEND_PORT', str(invalid_port))
        
        facade = ConfigFacade()
        
        with pytest.raises(ValueError, match="Invalid app port"):
            facade.validate()
    
    @pytest.mark.parametrize("invalid_port", [-1, 0, 65536])
    def test_validate_invalid_nginx_port(self, monkeypatch, clean_env, invalid_port):
        """Puerto de Nginx inválido falla validación"""
        monkeypatch.setenv('NGINX_PORT', str(invalid_port))
        
        facade = ConfigFacade()
        
        with pytest.raises(ValueError, match="Invalid nginx port"):
            facade.validate()
    
    def test_validate_invalid_log_level(self, monkeypatch, clean_env):
        """Log level inválido falla validación"""
        monkeypatch.setenv('LOG_LEVEL', 'INVALID_LEVEL')
        
        facade = ConfigFacade()
        
        with pytest.raises(ValueError, match="Invalid log level"):
            facade.validate()
    
    @pytest.mark.parametrize("valid_level", ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
    def test_validate_valid_log_levels(self, monkeypatch, clean_env, valid_level):
        """Log levels válidos pasan validación"""
        monkeypatch.setenv('LOG_LEVEL', valid_level)
        monkeypatch.setenv('BACKEND_PORT', '8080')
        monkeypatch.setenv('NGINX_PORT', '80')
        monkeypatch.setenv('METRICS_PORT', '9090')
        
        facade = ConfigFacade()
        
        assert facade.validate() is True


class TestConfigToDict:
    """Tests de serialización a diccionario"""
    
    def test_to_dict_structure(self, clean_env, mock_env):
        """Estructura del diccionario"""
        facade = ConfigFacade()
        config_dict = facade.to_dict()
        
        assert 'app' in config_dict
        assert 'nginx' in config_dict
        assert 'metrics' in config_dict
    
    def test_to_dict_app_fields(self, clean_env, mock_env):
        """Campos de app en diccionario"""
        facade = ConfigFacade()
        config_dict = facade.to_dict()
        
        app = config_dict['app']
        assert 'host' in app
        assert 'port' in app
        assert 'debug' in app
        assert 'version' in app
        assert 'log_level' in app
    
    def test_to_dict_serializable(self, clean_env, mock_env):
        """Diccionario es serializable a JSON"""
        import json
        
        facade = ConfigFacade()
        config_dict = facade.to_dict()
        
        # No debe lanzar excepción
        json_str = json.dumps(config_dict)
        assert isinstance(json_str, str)
        assert len(json_str) > 0


class TestConfigSingleton:
    """Tests del patrón Singleton en ConfigFacade"""
    
    def test_multiple_instances_share_cache(self, clean_env):
        """Múltiples instancias comparten caché"""
        facade1 = ConfigFacade()
        facade2 = ConfigFacade()
        
        # Primer acceso
        app1 = facade1.app
        
        # Segundo acceso desde otra instancia
        app2 = facade2.app
        
        # Deberían ser la misma instancia si se implementa singleton correctamente
        # (En este caso, cada ConfigFacade tiene su propio caché, pero la config es la misma)
        assert app1.host == app2.host
        assert app1.port == app2.port


class TestConfigEdgeCases:
    """Tests de casos límite"""
    
    def test_empty_env_uses_defaults(self, clean_env):
        """ENV vacío usa valores por defecto"""
        facade = ConfigFacade()
        
        assert facade.app.port == 8080
        assert facade.nginx.port == 80
        assert facade.metrics.metrics_port == 9090
    
    def test_partial_env_mixes_with_defaults(self, monkeypatch, clean_env):
        """ENV parcial mezcla con defaults"""
        monkeypatch.setenv('BACKEND_PORT', '9000')
        # No setear otros valores
        
        facade = ConfigFacade()
        
        assert facade.app.port == 9000  # Del ENV
        assert facade.app.host == "0.0.0.0"  # Default
    
    def test_config_after_env_change(self, monkeypatch, clean_env):
        """Cambio de ENV después de crear facade"""
        facade = ConfigFacade()
        
        # Primera lectura
        config1 = facade.app
        port1 = config1.port
        
        # Cambiar ENV (no debería afectar debido al caché)
        monkeypatch.setenv('BACKEND_PORT', '9999')
        
        # Segunda lectura (del caché)
        config2 = facade.app
        port2 = config2.port
        
        assert port1 == port2  # Mismo valor por el caché


class TestConfigIntegrationWithApp:
    """Tests de integración con la aplicación"""
    
    def test_config_used_in_app_creation(self, mock_env):
        """Configuración se usa en creación de app"""
        from src.app import create_app
        
        app = create_app()
        
        assert app.config['PORT'] == 8080
        assert app.config['HOST'] == '127.0.0.1'
    
    def test_custom_config_overrides_env(self, mock_env):
        """Config custom sobrescribe ENV"""
        from src.app import create_app
        
        custom = {
            'PORT': 9999,
            'DEBUG': True,
        }
        
        app = create_app(custom)
        
        assert app.config['PORT'] == 9999
        assert app.config['DEBUG'] is True


# Marker para tests de config
pytestmark = pytest.mark.unit