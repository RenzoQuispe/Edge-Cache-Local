"""
Fixtures compartidas para todos los tests.
Usa scopes optimizados y fixtures anidadas según las reglas.
"""
import pytest
import os
import tempfile
from typing import Generator, Dict, Any
from unittest.mock import Mock, MagicMock
from pathlib import Path

# Habilitar PEP 657 tracebacks mejorados
import sys
sys.tracebacklimit = 1000


@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory) -> Path:
    """Directorio temporal para datos de test (scope: session)"""
    return tmp_path_factory.mktemp("test_data")


@pytest.fixture(scope="module")
def sample_log_lines() -> list[str]:
    """Líneas de log de muestra para tests (scope: module, se reutiliza)"""
    return [
        '192.168.1.100 - [27/Oct/2025:10:00:00 +0000] "GET /api/static HTTP/1.1" 200 1234 0.050 "HIT"',
        '192.168.1.101 - [27/Oct/2025:10:00:01 +0000] "GET /api/static HTTP/1.1" 200 1234 0.045 "HIT"',
        '192.168.1.102 - [27/Oct/2025:10:00:02 +0000] "GET /api/dynamic HTTP/1.1" 200 567 0.120 "MISS"',
        '192.168.1.103 - [27/Oct/2025:10:00:03 +0000] "GET /api/no-cache HTTP/1.1" 200 890 0.080 "BYPASS"',
        '192.168.1.104 - [27/Oct/2025:10:00:04 +0000] "GET /api/data HTTP/1.1" 200 2345 0.095 "MISS"',
        '192.168.1.105 - [27/Oct/2025:10:00:05 +0000] "GET /api/data HTTP/1.1" 200 2345 0.035 "HIT"',
        '192.168.1.106 - [27/Oct/2025:10:00:06 +0000] "GET /api/static HTTP/1.1" 304 0 0.025 "HIT"',
        '192.168.1.107 - [27/Oct/2025:10:00:07 +0000] "GET /api/unknown HTTP/1.1" 404 512 0.090 "MISS"',
        '192.168.1.108 - [27/Oct/2025:10:00:08 +0000] "GET /api/error HTTP/1.1" 500 256 0.150 "MISS"',
        '192.168.1.109 - [27/Oct/2025:10:00:09 +0000] "GET /api/static HTTP/1.1" 200 1234 0.030 "HIT"',
    ]


@pytest.fixture
def clean_env(monkeypatch) -> Generator[None, None, None]:
    """
    Limpia variables de entorno antes de cada test (autouse-like behavior).
    Scope: function (se ejecuta para cada test).
    """
    # Guardar ENV originales
    original_env = os.environ.copy()
    
    # Limpiar variables relacionadas con la app
    env_vars = [
        'BACKEND_HOST', 'BACKEND_PORT', 'FLASK_DEBUG', 'APP_VERSION',
        'NGINX_HOST', 'NGINX_PORT', 'NGINX_CACHE_PATH',
        'METRICS_ENABLED', 'LOG_LEVEL'
    ]
    
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)
    
    yield
    
    # Restaurar ENV (cleanup)
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_env(monkeypatch) -> Dict[str, str]:
    """Configuración de entorno mock para tests"""
    env_config = {
        'BACKEND_HOST': '127.0.0.1',
        'BACKEND_PORT': '8080',
        'FLASK_DEBUG': 'false',
        'APP_VERSION': 'test-1.0.0',
        'NGINX_HOST': '0.0.0.0',
        'NGINX_PORT': '80',
        'METRICS_ENABLED': 'true',
        'LOG_LEVEL': 'DEBUG',
    }
    
    for key, value in env_config.items():
        monkeypatch.setenv(key, value)
    
    return env_config


@pytest.fixture
def temp_log_file(tmp_path, sample_log_lines) -> Path:
    """Crea un archivo de log temporal con datos de muestra"""
    log_file = tmp_path / "access.log"
    log_file.write_text('\n'.join(sample_log_lines))
    return log_file


@pytest.fixture
def empty_log_file(tmp_path) -> Path:
    """Archivo de log vacío"""
    log_file = tmp_path / "empty.log"
    log_file.touch()
    return log_file


@pytest.fixture
def flask_app():
    """
    Crea una instancia de Flask app para tests.
    Scope: function (nueva instancia por test).
    """
    from src.app import create_app
    
    app = create_app({
        'TESTING': True,
        'PORT': 8080,
        'DEBUG': False,
    })
    
    return app


@pytest.fixture
def flask_client(flask_app):
    """Cliente de test de Flask (anidada: depende de flask_app)"""
    return flask_app.test_client()


@pytest.fixture
def mock_response():
    """Mock de respuesta HTTP para tests"""
    mock = Mock()
    mock.status_code = 200
    mock.headers = {}
    mock.json.return_value = {'status': 'ok'}
    mock.text = '{"status": "ok"}'
    return mock


@pytest.fixture
def stub_curl_command(monkeypatch):
    """
    Stub para comando curl (no ejecuta binario real).
    Útil para tests de integración sin dependencias externas.
    """
    def fake_curl(*args, **kwargs):
        """Simula salida de curl"""
        return Mock(
            returncode=0,
            stdout='{"status": "ok", "cache": "HIT"}',
            stderr=''
        )
    
    import subprocess
    monkeypatch.setattr(subprocess, 'run', fake_curl)
    return fake_curl


@pytest.fixture
def stub_system_binaries(monkeypatch):
    """Stub para múltiples binarios del sistema"""
    stubs = {}
    
    def create_stub(cmd: str, output: str):
        def stub_fn(*args, **kwargs):
            return Mock(returncode=0, stdout=output, stderr='')
        return stub_fn
    
    stubs['curl'] = create_stub('curl', '{"data": "test"}')
    stubs['ab'] = create_stub('ab', 'Requests per second: 1000')
    stubs['wrk'] = create_stub('wrk', 'Latency: 10ms')
    
    import subprocess
    original_run = subprocess.run
    
    def smart_run(args, *run_args, **run_kwargs):
        """Intercepta llamadas a subprocess.run"""
        if isinstance(args, list) and args[0] in stubs:
            return stubs[args[0]]()
        return original_run(args, *run_args, **run_kwargs)
    
    monkeypatch.setattr(subprocess, 'run', smart_run)
    return stubs


@pytest.fixture(autouse=True)
def reset_singletons():
    """
    Fixture autouse para resetear singletons entre tests.
    Scope: function (se ejecuta automáticamente para cada test).
    """
    # Resetear ConfigFacade singleton si existe
    from src import config
    if hasattr(config, 'config'):
        config.config._app = None
        config.config._nginx = None
        config.config._metrics = None
    
    yield
    
    # Cleanup después del test
    pass


@pytest.fixture
def metrics_analyzer():
    """Instancia de MetricsAnalyzer para tests"""
    from src.metrics import MetricsAnalyzer
    return MetricsAnalyzer()


# Parametrización común para cache policies
CACHE_POLICIES = [
    ('max-age', 3600, False, True),
    ('must-revalidate', 60, True, True),
    ('no-store', 0, False, False),
    ('private', 300, False, False),
]


@pytest.fixture(params=CACHE_POLICIES, ids=['max-age', 'must-revalidate', 'no-store', 'private'])
def cache_policy_params(request):
    """Parametrización de políticas de caché"""
    return {
        'name': request.param[0],
        'max_age': request.param[1],
        'must_revalidate': request.param[2],
        'public': request.param[3],
    }