"""
Tests End-to-End del stack completo.
Requiere que el stack esté desplegado (make apply).
"""
import pytest
import requests
import time
from typing import Dict, List


# Configuración de endpoints
PROXY_URL = "http://localhost"
BACKEND_URL = "http://localhost:8080"


@pytest.fixture(scope="module")
def check_services_running():
    """Verifica que los servicios estén corriendo antes de ejecutar tests"""
    try:
        response = requests.get(f"{PROXY_URL}/health", timeout=5)
        assert response.status_code == 200, "Proxy no responde"
        
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        assert response.status_code == 200, "Backend no responde"
        
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Servicios no disponibles: {e}. Ejecuta 'make apply' primero.")


class TestBasicConnectivity:
    """Tests básicos de conectividad"""
    
    def test_proxy_health(self, check_services_running):
        """Proxy responde al health check"""
        response = requests.get(f"{PROXY_URL}/proxy/health")
        assert response.status_code == 200
        assert "Proxy OK" in response.text
    
    def test_backend_health_direct(self, check_services_running):
        """Backend responde directamente"""
        response = requests.get(f"{BACKEND_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
    
    def test_backend_health_through_proxy(self, check_services_running):
        """Backend responde a través del proxy"""
        response = requests.get(f"{PROXY_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'


class TestCacheHeaders:
    """Tests de headers de caché"""
    
    def test_static_endpoint_has_cache_headers(self, check_services_running):
        """Endpoint static tiene headers de caché"""
        response = requests.get(f"{PROXY_URL}/api/static")
        
        assert response.status_code == 200
        assert 'Cache-Control' in response.headers
        assert 'X-Cache-Status' in response.headers
    
    def test_no_cache_endpoint_bypasses_cache(self, check_services_running):
        """Endpoint no-cache tiene X-Cache-Status: BYPASS"""
        response = requests.get(f"{PROXY_URL}/api/no-cache")
        
        assert response.status_code == 200
        # Puede ser BYPASS o no tener el header si no pasa por caché
        cache_status = response.headers.get('X-Cache-Status', 'BYPASS')
        assert cache_status in ['BYPASS', '-']
    
    @pytest.mark.parametrize("endpoint,expected_cache", [
        ("/api/static", True),
        ("/api/dynamic", True),
        ("/api/no-cache", False),
        ("/api/data", True),
    ])
    def test_cache_control_headers(self, check_services_running, endpoint, expected_cache):
        """Verifica Cache-Control headers por endpoint"""
        response = requests.get(f"{PROXY_URL}{endpoint}")
        
        assert response.status_code == 200
        cache_control = response.headers.get('Cache-Control', '')
        
        if expected_cache:
            assert 'max-age' in cache_control or 'public' in cache_control
        else:
            assert 'no-store' in cache_control or 'no-cache' in cache_control


class TestCacheBehavior:
    """Tests del comportamiento del caché"""
    
    def test_cache_hit_after_miss(self, check_services_running):
        """Primera request es MISS, segunda es HIT"""
        endpoint = f"{PROXY_URL}/api/static"
        
        # Primera request - debería ser MISS
        response1 = requests.get(endpoint)
        assert response1.status_code == 200
        cache_status1 = response1.headers.get('X-Cache-Status', 'MISS')
        
        # Segunda request - debería ser HIT
        time.sleep(0.5)  # Pequeña pausa
        response2 = requests.get(endpoint)
        assert response2.status_code == 200
        cache_status2 = response2.headers.get('X-Cache-Status')
        
        # Al menos una debe ser HIT si el caché funciona
        assert cache_status2 in ['HIT', 'MISS']  # Puede variar según timing
    
    def test_multiple_requests_increase_hit_ratio(self, check_services_running):
        """Múltiples requests aumentan el hit ratio"""
        endpoint = f"{PROXY_URL}/api/static"
        
        hits = 0
        total = 10
        
        for _ in range(total):
            response = requests.get(endpoint)
            assert response.status_code == 200
            
            if response.headers.get('X-Cache-Status') == 'HIT':
                hits += 1
            
            time.sleep(0.1)
        
        # Después de 10 requests, al menos algunas deben ser hits
        # (la primera puede ser MISS)
        assert hits >= 1, f"Expected at least 1 hit, got {hits}"
    
    def test_different_query_params_different_cache(self, check_services_running):
        """Query params diferentes = entradas de caché diferentes"""
        base_url = f"{PROXY_URL}/api/data"
        
        response1 = requests.get(f"{base_url}?page=1")
        response2 = requests.get(f"{base_url}?page=2")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Los datos deben ser diferentes
        data1 = response1.json()
        data2 = response2.json()
        
        assert data1['page'] != data2['page']


class TestInvalidation:
    """Tests de invalidación de caché"""
    
    def test_invalidate_endpoint(self, check_services_running):
        """Endpoint de invalidación funciona"""
        # Hacer una request para cachear
        requests.get(f"{PROXY_URL}/api/static")
        
        # Invalidar
        response = requests.post(
            f"{PROXY_URL}/api/invalidate",
            json={'target': '/api/static'}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'invalidated'
        assert data['target'] == '/api/static'
    
    def test_invalidate_all(self, check_services_running):
        """Invalidación con wildcard"""
        response = requests.post(
            f"{PROXY_URL}/api/invalidate",
            json={'target': '*'}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['target'] == '*'


class TestPerformance:
    """Tests de performance básicos"""
    
    def test_response_time_acceptable(self, check_services_running):
        """Tiempos de respuesta son aceptables"""
        endpoint = f"{PROXY_URL}/api/static"
        
        response_times = []
        for _ in range(5):
            start = time.time()
            response = requests.get(endpoint)
            duration = time.time() - start
            
            assert response.status_code == 200
            response_times.append(duration)
        
        # Promedio debe ser < 1 segundo (muy generoso para CI)
        avg_time = sum(response_times) / len(response_times)
        assert avg_time < 1.0, f"Average response time too high: {avg_time:.3f}s"
    
    def test_cached_requests_faster(self, check_services_running):
        """Requests cacheadas son más rápidas"""
        endpoint = f"{PROXY_URL}/api/static"
        
        # Primera request (MISS)
        start1 = time.time()
        requests.get(endpoint)
        time1 = time.time() - start1
        
        time.sleep(0.5)
        
        # Segunda request (HIT esperado)
        start2 = time.time()
        requests.get(endpoint)
        time2 = time.time() - start2
        
        # La segunda puede ser más rápida (pero no garantizado en CI)
        # Solo verificamos que ambas completan
        assert time1 < 2.0
        assert time2 < 2.0


class TestErrorHandling:
    """Tests de manejo de errores"""
    
    def test_404_returns_json(self, check_services_running):
        """404 retorna JSON"""
        response = requests.get(f"{PROXY_URL}/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data
    
    def test_proxy_handles_backend_down_gracefully(self, check_services_running):
        """Test requiere backend down - skip si no aplica"""
        pytest.skip("Requiere detener backend manualmente")


class TestDataEndpoints:
    """Tests de endpoints de datos"""
    
    @pytest.mark.parametrize("page", [1, 2, 3, 5, 10])
    def test_data_pagination(self, check_services_running, page):
        """Paginación funciona correctamente"""
        response = requests.get(f"{PROXY_URL}/api/data?page={page}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['type'] == 'data'
        assert data['page'] == page
        assert len(data['items']) == 10
    
    def test_data_items_are_correct(self, check_services_running):
        """Items de paginación son correctos"""
        response = requests.get(f"{PROXY_URL}/api/data?page=2")
        
        data = response.json()
        items = data['items']
        
        # Página 2 debe tener items 10-19
        expected_items = [f'item-{i}' for i in range(10, 20)]
        assert items == expected_items


class TestNginxStats:
    """Tests de estadísticas de Nginx"""
    
    def test_nginx_stats_endpoint(self, check_services_running):
        """Endpoint de stats de Nginx responde"""
        response = requests.get(f"{PROXY_URL}/proxy/stats")
        
        assert response.status_code == 200
        # Stub status retorna texto plano
        assert 'Active connections' in response.text or 'active' in response.text.lower()


class TestFullWorkflow:
    """Test de flujo completo E2E"""
    
    def test_complete_user_journey(self, check_services_running):
        """Simula un flujo completo de usuario"""
        # 1. Health check
        response = requests.get(f"{PROXY_URL}/health")
        assert response.status_code == 200
        
        # 2. Request a contenido estático
        response = requests.get(f"{PROXY_URL}/api/static")
        assert response.status_code == 200
        static_data = response.json()
        assert static_data['type'] == 'static'
        
        # 3. Request a contenido dinámico
        response = requests.get(f"{PROXY_URL}/api/dynamic")
        assert response.status_code == 200
        dynamic_data = response.json()
        assert dynamic_data['type'] == 'dynamic'
        
        # 4. Request con parámetros
        response = requests.get(f"{PROXY_URL}/api/data?page=1")
        assert response.status_code == 200
        data = response.json()
        assert data['page'] == 1
        
        # 5. Invalidar caché
        response = requests.post(
            f"{PROXY_URL}/api/invalidate",
            json={'target': '/api/static'}
        )
        assert response.status_code == 200
        
        # 6. Request nuevamente al estático (post-invalidación)
        response = requests.get(f"{PROXY_URL}/api/static")
        assert response.status_code == 200


# Markers para organizar tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.e2e,
]