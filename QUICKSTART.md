# Guía Rápida - Edge Cache Local

## Paso 1: Preparar el entorno

```bash
# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
make tools
```

## Paso 2: Verificar que funciona localmente

```bash
# Ejecutar tests
make test

# Ver cobertura
make coverage

# Ejecutar linters
make lint
```

## Paso 3: Construir y ejecutar

### Opción A: Sin Docker (desarrollo rápido)

```bash
# Terminal 1: Backend
make run

# Terminal 2: Probar
curl http://localhost:8080/health
curl http://localhost:8080/api/static
```

### Opción B: Con Docker (más realista)

```bash
# Construir imagen
make build

# Ejecutar solo el backend
make run-docker

# Verificar
curl http://localhost:8080/health
```

## Paso 4: Desplegar con Terraform (Full Stack)

Primero modificar `nginx_config_path` con su ruta absoluta al `nginx.conf`, y entonces:

```bash
# Inicializar Terraform
make tf-init

# Ver qué se va a crear
make plan

# Desplegar todo (backend + proxy + monitor).  MONITOR AUN NO FUNCIONAL
make apply

# Verificar servicios
curl http://localhost/health           # A través del proxy
curl http://localhost/api/static       # Endpoint con caché
curl -I http://localhost/api/static    # Ver headers de caché
```

## Paso 5: Verificar métricas

```bash
# Generar tráfico de prueba
for i in {1..100}; do
  curl -s http://localhost/api/static > /dev/null
  curl -s http://localhost/api/dynamic > /dev/null
done

# Analizar métricas
make metrics

# Ver logs
make logs-proxy
```

## Paso 6: Smoke Tests

```bash
# Ejecutar smoke tests
make smoke

# Debería ver:
# ✓ Health check passed
# ✓ Static endpoint passed
# ✓ Dynamic endpoint passed
# ✓ Smoke tests passed
```

## Paso 7: Limpiar

```bash
# Destruir infraestructura
make destroy

# O manualmente si el make falla
docker stop $(docker ps -aq)
docker rm $(docker ps -aq)
docker volume prune -f
docker network prune -f

# Limpiar archivos generados
make clean
```