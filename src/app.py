"""
Backend service con soporte para headers de caché y métricas.
"""
import os
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, Response, request, jsonify
from dataclasses import dataclass, asdict

# Configuración de logging para métricas
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CachePolicy:
    """Define políticas de caché para diferentes endpoints"""
    max_age: int
    must_revalidate: bool = False
    no_store: bool = False
    public: bool = True

    def to_header(self) -> str:
        """Convierte la política a header Cache-Control"""
        parts = []
        
        if self.no_store:
            return "no-store, no-cache, must-revalidate"
        
        visibility = "public" if self.public else "private"
        parts.append(visibility)
        parts.append(f"max-age={self.max_age}")
        
        if self.must_revalidate:
            parts.append("must-revalidate")
        
        return ", ".join(parts)

class CacheConfig:
    """Configuración de políticas de caché por ruta"""
    POLICIES: Dict[str, CachePolicy] = {
        "/api/static": CachePolicy(max_age=3600, public=True),
        "/api/dynamic": CachePolicy(max_age=60, must_revalidate=True),
        "/api/no-cache": CachePolicy(max_age=0, no_store=True),
        "/api/data": CachePolicy(max_age=300, public=True),
    }

    @classmethod
    def get_policy(cls, path: str) -> Optional[CachePolicy]:
        """Obtiene política para una ruta"""
        return cls.POLICIES.get(path)

def create_app(config: Optional[Dict[str, Any]] = None) -> Flask:
    """Factory para crear la aplicación Flask"""
    app = Flask(__name__)
    
    # Configuración 12-Factor desde ENV
    app.config.update({
        'PORT': int(os.getenv('BACKEND_PORT', 8080)),
        'HOST': os.getenv('BACKEND_HOST', '0.0.0.0'),
        'DEBUG': os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
        'VERSION': os.getenv('APP_VERSION', '1.0.0'),
    })
    
    if config:
        app.config.update(config)

    @app.before_request
    def log_request():
        """Log de cada request para métricas"""
        request.start_time = time.time()
        logger.info(
            "REQUEST",
            extra={
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_agent': request.user_agent.string,
            }
        )

    @app.after_request
    def log_response(response: Response) -> Response:
        """Log de respuesta con timing y headers de caché"""
        duration = time.time() - getattr(request, 'start_time', time.time())
        
        # Aplicar política de caché
        policy = CacheConfig.get_policy(request.path)
        if policy:
            response.headers['Cache-Control'] = policy.to_header()
            response.headers['X-Cache-Policy'] = 'HIT' if policy.max_age > 0 else 'BYPASS'
        
        # Headers adicionales para tracking
        response.headers['X-Response-Time'] = f"{duration:.4f}"
        response.headers['X-Backend-Server'] = app.config['VERSION']
        
        logger.info(
            "RESPONSE",
            extra={
                'method': request.method,
                'path': request.path,
                'status': response.status_code,
                'duration_ms': duration * 1000,
                'cache_control': response.headers.get('Cache-Control', 'none'),
            }
        )
        
        return response

    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': app.config['VERSION']
        })

    @app.route('/api/static', methods=['GET'])
    def static_content():
        """Contenido estático cacheable por largo tiempo"""
        return jsonify({
            'type': 'static',
            'data': 'Este contenido no cambia frecuentemente',
            'timestamp': datetime.utcnow().isoformat(),
            'cache_hint': 'max-age=3600'
        })

    @app.route('/api/dynamic', methods=['GET'])
    def dynamic_content():
        """Contenido dinámico con revalidación"""
        return jsonify({
            'type': 'dynamic',
            'data': f'Contenido generado: {time.time()}',
            'timestamp': datetime.utcnow().isoformat(),
            'cache_hint': 'max-age=60, must-revalidate'
        })

    @app.route('/api/no-cache', methods=['GET'])
    def no_cache_content():
        """Contenido que nunca debe cachearse"""
        return jsonify({
            'type': 'no-cache',
            'data': f'Siempre fresco: {time.time()}',
            'timestamp': datetime.utcnow().isoformat(),
            'cache_hint': 'no-store'
        })

    @app.route('/api/data', methods=['GET'])
    def data_endpoint():
        """Endpoint de datos con caché moderado"""
        page = request.args.get('page', 1, type=int)
        return jsonify({
            'type': 'data',
            'page': page,
            'items': [f'item-{i}' for i in range((page-1)*10, page*10)],
            'timestamp': datetime.utcnow().isoformat(),
            'cache_hint': 'max-age=300'
        })

    @app.route('/api/invalidate', methods=['POST'])
    def invalidate_cache():
        """Endpoint para simular invalidación de caché"""
        target = request.json.get('target', '*') if request.json else '*'
        logger.info(f"CACHE_INVALIDATE target={target}")
        
        return jsonify({
            'status': 'invalidated',
            'target': target,
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    @app.errorhandler(404)
    def not_found(error):
        """Handler para 404"""
        return jsonify({
            'error': 'Not Found',
            'path': request.path
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handler para 500"""
        logger.error(f"Internal error: {error}")
        return jsonify({
            'error': 'Internal Server Error'
        }), 500

    return app

def main():
    """Punto de entrada principal"""
    app = create_app()
    port = app.config['PORT']
    host = app.config['HOST']
    
    logger.info(f"Starting backend server on {host}:{port}")
    app.run(host=host, port=port, debug=app.config['DEBUG'])

if __name__ == '__main__':
    main()