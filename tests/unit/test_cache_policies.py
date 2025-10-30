"""
Tests específicos de políticas de caché.
Pruebas parametrizadas exhaustivas de diferentes configuraciones.
"""
import pytest
from src.app import CachePolicy, CacheConfig


class TestCachePolicyCreation:
    """Tests de creación de políticas de caché"""
    
    @pytest.mark.parametrize("max_age,expected", [
        (0, 0),
        (60, 60),
        (3600, 3600),
        (86400, 86400),
    ])
    def test_create_policy_with_max_age(self, max_age, expected):
        """Crear política con diferentes max-age"""
        policy = CachePolicy(max_age=max_age)
        assert policy.max_age == expected
    
    def test_default_values(self):
        """Valores por defecto de la política"""
        policy = CachePolicy(max_age=100)
        
        assert policy.must_revalidate is False
        assert policy.no_store is False
        assert policy.public is True
    
    @pytest.mark.parametrize("must_revalidate", [True, False])
    def test_must_revalidate_flag(self, must_revalidate):
        """Flag must_revalidate"""
        policy = CachePolicy(max_age=60, must_revalidate=must_revalidate)
        assert policy.must_revalidate == must_revalidate
    
    @pytest.mark.parametrize("public", [True, False])
    def test_public_private(self, public):
        """Política pública vs privada"""
        policy = CachePolicy(max_age=60, public=public)
        assert policy.public == public


class TestCachePolicyToHeader:
    """Tests de conversión de política a header"""
    
    @pytest.mark.parametrize("max_age,must_revalidate,expected_parts", [
        (3600, False, ["public", "max-age=3600"]),
        (60, True, ["public", "max-age=60", "must-revalidate"]),
        (300, False, ["public", "max-age=300"]),
    ])
    def test_header_format(self, max_age, must_revalidate, expected_parts):
        """Formato correcto del header"""
        policy = CachePolicy(max_age=max_age, must_revalidate=must_revalidate)
        header = policy.to_header()
        
        for part in expected_parts:
            assert part in header
    
    def test_no_store_overrides_everything(self):
        """no_store sobrescribe otras configuraciones"""
        policy = CachePolicy(
            max_age=3600,
            must_revalidate=True,
            no_store=True
        )
        header = policy.to_header()
        
        assert "no-store" in header
        assert "no-cache" in header
        assert "must-revalidate" in header
        # No debe incluir max-age cuando no_store=True
        assert "max-age" not in header
    
    def test_private_cache(self):
        """Caché privado"""
        policy = CachePolicy(max_age=300, public=False)
        header = policy.to_header()
        
        assert "private" in header
        assert "public" not in header
    
    @pytest.mark.parametrize("invalid_max_age", [-1, -100, -3600])
    def test_negative_max_age_handled(self, invalid_max_age):
        """Max-age negativo (caso límite)"""
        policy = CachePolicy(max_age=invalid_max_age)
        header = policy.to_header()
        
        # Debe generar header aunque el valor sea inválido
        assert isinstance(header, str)
        assert len(header) > 0


class TestCacheConfigGetPolicy:
    """Tests de obtención de políticas por ruta"""
    
    @pytest.mark.parametrize("path,expected_max_age", [
        ("/api/static", 3600),
        ("/api/dynamic", 60),
        ("/api/no-cache", 0),
        ("/api/data", 300),
    ])
    def test_get_policy_for_known_paths(self, path, expected_max_age):
        """Políticas correctas para rutas conocidas"""
        policy = CacheConfig.get_policy(path)
        
        assert policy is not None
        assert policy.max_age == expected_max_age
    
    @pytest.mark.parametrize("unknown_path", [
        "/api/unknown",
        "/nonexistent",
        "/",
        "",
        "/api/static/extra",
    ])
    def test_get_policy_for_unknown_paths(self, unknown_path):
        """Rutas desconocidas retornan None"""
        policy = CacheConfig.get_policy(unknown_path)
        assert policy is None
    
    def test_static_policy_details(self):
        """Detalles de la política static"""
        policy = CacheConfig.get_policy("/api/static")
        
        assert policy.max_age == 3600
        assert policy.public is True
        assert policy.must_revalidate is False
        assert policy.no_store is False
    
    def test_dynamic_policy_details(self):
        """Detalles de la política dynamic"""
        policy = CacheConfig.get_policy("/api/dynamic")
        
        assert policy.max_age == 60
        assert policy.must_revalidate is True
    
    def test_no_cache_policy_details(self):
        """Detalles de la política no-cache"""
        policy = CacheConfig.get_policy("/api/no-cache")
        
        assert policy.max_age == 0
        assert policy.no_store is True


class TestCachePolicyEdgeCases:
    """Tests de casos límite"""
    
    def test_zero_max_age(self):
        """max-age=0 es válido"""
        policy = CachePolicy(max_age=0)
        header = policy.to_header()
        
        assert "max-age=0" in header
    
    def test_very_large_max_age(self):
        """max-age muy grande"""
        policy = CachePolicy(max_age=31536000)  # 1 año
        header = policy.to_header()
        
        assert "max-age=31536000" in header
    
    def test_all_flags_true(self):
        """Todas las flags en True"""
        policy = CachePolicy(
            max_age=60,
            must_revalidate=True,
            no_store=True,
            public=True
        )
        header = policy.to_header()
        
        # no_store domina
        assert "no-store" in header
    
    def test_all_flags_false_except_max_age(self):
        """Solo max-age configurado"""
        policy = CachePolicy(
            max_age=120,
            must_revalidate=False,
            no_store=False,
            public=True
        )
        header = policy.to_header()
        
        assert "max-age=120" in header
        assert "public" in header
        assert "must-revalidate" not in header


class TestCachePolicyComparison:
    """Tests de comparación entre políticas"""
    
    def test_policies_are_independent(self):
        """Políticas son independientes entre sí"""
        policy1 = CacheConfig.get_policy("/api/static")
        policy2 = CacheConfig.get_policy("/api/dynamic")
        
        assert policy1.max_age != policy2.max_age
        assert policy1.must_revalidate != policy2.must_revalidate
    
    def test_same_path_returns_same_policy(self):
        """Misma ruta retorna misma política"""
        policy1 = CacheConfig.get_policy("/api/static")
        policy2 = CacheConfig.get_policy("/api/static")
        
        assert policy1.max_age == policy2.max_age
        assert policy1.must_revalidate == policy2.must_revalidate
        assert policy1.public == policy2.public


class TestCachePolicyIntegration:
    """Tests de integración con Flask"""
    
    def test_policy_applied_to_response(self, flask_client):
        """Política se aplica correctamente a la respuesta"""
        response = flask_client.get('/api/static')
        
        assert response.status_code == 200
        assert 'Cache-Control' in response.headers
        
        cache_control = response.headers['Cache-Control']
        assert 'max-age=3600' in cache_control
    
    def test_different_endpoints_different_policies(self, flask_client):
        """Diferentes endpoints tienen diferentes políticas"""
        static_response = flask_client.get('/api/static')
        dynamic_response = flask_client.get('/api/dynamic')
        
        static_cc = static_response.headers['Cache-Control']
        dynamic_cc = dynamic_response.headers['Cache-Control']
        
        assert static_cc != dynamic_cc
        assert 'max-age=3600' in static_cc
        assert 'max-age=60' in dynamic_cc


# Marker para tests de cache policies
pytestmark = pytest.mark.unit