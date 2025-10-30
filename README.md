# Edge-Cache Local - Proyecto 7

CDN casera con Nginx + caché, backend Flask y métricas de performance. 

## Marco Teórico

Una CDN (Red de Entrega de Contenido) es un conjunto de servidores distribuidos geográficamente que almacenan copias en caché del contenido de un sitio web (imágenes, videos, archivos, HTML, etc.) para entregarlo más rápido al usuario final.
En lugar de que cada usuario tenga que conectarse al servidor principal (backend), una CDN coloca servidores intermedios (proxies cache) cerca de los usuarios.
- Si el contenido ya está cacheado → se sirve directamente desde la CDN (respuesta más rápida).
- Si no está cacheado → la CDN lo pide al backend, lo guarda y luego lo entrega.

### CDN “casera”

Tu proyecto **simula una CDN local** usando **Nginx como reverse proxy con caché**.

En este contexto:

| Componente                | Rol                                                                                       |
| ------------------------- | ----------------------------------------------------------------------------------------- |
| **Nginx**                 | Actúa como proxy-cache. Guarda las respuestas del backend y las sirve si aún son válidas. |
| **Backend (Python o Go)** | Genera las respuestas dinámicas.                                                          |
| **Prometheus o logs**     | Mide el ratio de hits/misses, latencias, errores, etc.                                    |
| **Terraform**             | Orquesta los contenedores (proxy, app, monitor) automáticamente.                          |
| **pytest**                | Testea las políticas de cache (`max-age`, `no-store`, `must-revalidate`, etc).            |

### Conceptos clave

| Término               | Significado                                                                     |
| --------------------- | ------------------------------------------------------------------------------- |
| **Reverse Proxy**     | Servidor intermedio que recibe peticiones del cliente y las reenvía al backend. |
| **Cache Hit**         | Petición servida desde la caché (sin consultar al backend).                     |
| **Cache Miss**        | Petición que tuvo que consultar al backend.                                     |
| **Invalidación**      | Eliminar entradas obsoletas (por tiempo o por cambio manual).                   |
| **Hit Ratio**         | Porcentaje de peticiones que se sirvieron desde la caché. (Meta ≥ 80%)          |
| **Drift (Terraform)** | Diferencia entre lo que Terraform cree desplegado y el estado real (meta: 0%).  |

## Objetivos

Implementar un reverse proxy con caché (Nginx) delante de un servicio backend, con:
- Políticas de cacheo configurables por endpoint
- Invalidación selectiva de caché
- Observabilidad de hit/miss ratio
- Orquestación local con Terraform (Docker provider)
- Métricas de latencia P50/P95/P99
- Cobertura de tests ≥90%

## Arquitectura

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Cliente   │────▶│  Nginx Proxy     │────▶│   Backend   │
│             │     │  (Edge Cache)    │     │   (Flask)   │
└─────────────┘     └──────────────────┘     └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Monitor    │
                     │  (Métricas)  │
                     └──────────────┘
```

### Componentes

1. **Backend (Flask)**
   - Servicio con múltiples endpoints
   - Cache-Control headers configurables
   - Health checks
   - Logs estructurados

2. **Proxy (Nginx)**
   - Reverse proxy con caché
   - Políticas diferenciadas por ruta
   - Invalidación selectiva
   - Logs con cache status

3. **Monitor**
   - Análisis de logs
   - Cálculo de hit ratio
   - Métricas de latencia

## Quick Start

### Prerrequisitos

- Python 3.11+
- Docker y Docker Compose
- Terraform >= 1.0
- Make

### Instalación

```bash
# Instalar dependencias
make tools

# Inicializar Terraform
make tf-init

# Desplegar infraestructura
make apply
```

Los servicios estarán disponibles en:
- **Proxy (punto de entrada)**: http://localhost:80
- **Backend (directo)**: http://localhost:8081
- **Monitor**: http://localhost:9090

### Verificación

```bash
# Health check
curl http://localhost/health

# Endpoint con caché
curl http://localhost/api/static

# Ver hit/miss en headers
curl -I http://localhost/api/static
```

## Comandos Disponibles

```bash
make help              # Ver todos los comandos
make tools             # Instalar dependencias
make build             # Construir imagen Docker
make test              # Ejecutar tests
make coverage          # Reporte de cobertura (≥90%)
make lint              # Linters
make format            # Formatear código
make plan              # Terraform plan
make apply             # Desplegar infraestructura
make destroy           # Destruir infraestructura
make metrics           # Analizar métricas
make smoke             # Smoke tests
```

### Métricas Disponibles

- **Cache Metrics**:
  - Hit Ratio (objetivo: ≥80%)
  - Cache Hits/Misses/Bypass
  
- **Latencia**:
  - P50, P95, P99
  - Objetivo P95 < 200ms

- **Errores**:
  - Error Rate (5xx)
  - Objetivo < 1%

- **Throughput**:
  - Total requests
  - Bytes transferidos

## Configuración

### Variables de Entorno (12-Factor)

```bash
# Backend
export BACKEND_HOST=0.0.0.0
export BACKEND_PORT=8080
export FLASK_DEBUG=false
export APP_VERSION=1.0.0
export LOG_LEVEL=INFO

# Nginx
export NGINX_PORT=80
export NGINX_CACHE_PATH=/var/cache/nginx
export NGINX_CACHE_SIZE=100m
export NGINX_CACHE_MAX_SIZE=1g

# Monitor
export METRICS_ENABLED=true
export METRICS_PORT=9090
```

### Políticas de Caché

| Endpoint | Max-Age | Revalidate | Comportamiento |
|----------|---------|------------|----------------|
| `/api/static` | 3600s | No | Caché largo |
| `/api/dynamic` | 60s | Sí | Caché corto con revalidación |
| `/api/no-cache` | 0s | - | Sin caché (bypass) |
| `/api/data` | 300s | No | Caché moderado |

### Invalidación de Caché

```bash
# Invalidar endpoint específico
curl -X POST http://localhost/api/invalidate \
  -H "Content-Type: application/json" \
  -d '{"target": "/api/static"}'

# Invalidar todo
curl -X POST http://localhost/api/invalidate \
  -H "Content-Type: application/json" \
  -d '{"target": "*"}'

# Purgar vía proxy (requiere acceso local)
curl -X PURGE http://localhost/proxy/purge/api/static
```

## Infraestructura como Código

### Estructura de Terraform

```
infra/terraform/
├── modules/
│   ├── backend/      # Módulo componible del backend
│   ├── proxy/        # Módulo del proxy Nginx
│   └── monitor/      # Módulo de monitoreo
└── stacks/
    └── local-dev/    # Stack completo (Composite pattern)
```

### Verificar Drift

```bash
# Verificar si hay drift
make tf-drift

# Si hay drift, ver diferencias
cd infra/terraform/stacks/local-dev
terraform plan
```

### Validaciones

```bash
# Validar sintaxis
make tf-validate

# Linter (tflint)
make tf-lint

# Seguridad (tfsec)
make tf-sec
```

## CI/CD

### GitHub Actions

```yaml
# .github/workflows/ci.yml
- Lint y formato
- Tests con cobertura ≥90%
- Detección de secretos
- Validación de IaC
- Actualización automática de tablero
```

### Gates

1. **Calidad**: lint/format
2. **Tests**: pytest + cobertura ≥90%
3. **IaC**: terraform fmt/validate + tflint/tfsec
4. **Seguridad**: detección de secretos
5. **Projects**: movimiento automático de tarjetas

## Criterios de Aceptación

- [x] Hit ratio ≥80% en E2E
- [x] Cobertura ≥90%
- [x] Terraform reproducible (0% drift)
- [x] PRs con checklist de seguridad
- [x] Video mostrando tablero y métricas
- [x] CI verde con todos los gates