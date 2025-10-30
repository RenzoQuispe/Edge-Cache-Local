.PHONY: help tools build test run pack clean plan apply destroy lint format coverage

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
BLACK := $(PYTHON) -m black
ISORT := $(PYTHON) -m isort
FLAKE8 := $(PYTHON) -m flake8
TERRAFORM := terraform
DOCKER := docker
DOCKER_COMPOSE := docker-compose

# Directorios
SRC_DIR := src
TEST_DIR := tests
INFRA_DIR := infra/terraform/stacks/local-dev

# Nombres de imágenes
BACKEND_IMAGE := edge-cache-backend:latest
PROXY_IMAGE := nginx:alpine

help: ## Muestra esta ayuda
	@echo "Edge-Cache Local - Comandos disponibles:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

tools: ## Instala herramientas de desarrollo
	@echo "Instalando herramientas..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	@echo "✓ Herramientas instaladas"

build: ## Construye la imagen Docker del backend
	@echo "Construyendo imagen del backend..."
	$(DOCKER) build -t $(BACKEND_IMAGE) -f Dockerfile .
	@echo "✓ Imagen construida: $(BACKEND_IMAGE)"

test: ## Ejecuta todos los tests con pytest
	@echo "Ejecutando tests..."
	$(PYTEST) $(TEST_DIR) -v --tb=short
	@echo "✓ Tests completados"

test-unit: ## Ejecuta solo tests unitarios
	@echo "Ejecutando tests unitarios..."
	$(PYTEST) $(TEST_DIR)/unit -v
	@echo "✓ Tests unitarios completados"

test-integration: ## Ejecuta tests de integración
	@echo "Ejecutando tests de integración..."
	$(PYTEST) $(TEST_DIR)/integration -v
	@echo "✓ Tests de integración completados"

test-parametrized: ## Ejecuta tests con casos límite (parametrizados)
	@echo "Ejecutando tests parametrizados..."
	$(PYTEST) $(TEST_DIR) -v -k "parametrize"
	@echo "✓ Tests parametrizados completados"

coverage: ## Genera reporte de cobertura (gate ≥90%)
	@echo "Generando reporte de cobertura..."
	$(PYTEST) $(TEST_DIR) \
		--cov=$(SRC_DIR) \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=90
	@echo "✓ Reporte generado en htmlcov/index.html"

lint: ## Ejecuta linters (flake8)
	@echo "Ejecutando linters..."
	$(FLAKE8) $(SRC_DIR) $(TEST_DIR) --max-line-length=120 --exclude=__pycache__,*.pyc
	@echo "✓ Linting completado"

format: ## Formatea código con black e isort
	@echo "Formateando código..."
	$(BLACK) $(SRC_DIR) $(TEST_DIR) --line-length=120
	$(ISORT) $(SRC_DIR) $(TEST_DIR) --profile black
	@echo "✓ Código formateado"

format-check: ## Verifica formato sin modificar
	@echo "Verificando formato..."
	$(BLACK) $(SRC_DIR) $(TEST_DIR) --check --line-length=120
	$(ISORT) $(SRC_DIR) $(TEST_DIR) --check-only --profile black
	@echo "✓ Formato verificado"

run: ## Ejecuta el backend localmente (sin Docker)
	@echo "Ejecutando backend..."
	FLASK_APP=src/app.py BACKEND_PORT=8080 $(PYTHON) -m src.app

run-docker: build ## Ejecuta el backend en Docker
	@echo "Ejecutando backend en Docker..."
	$(DOCKER) run -d \
		--name edge-cache-backend \
		-p 8080:8080 \
		-e BACKEND_PORT=8080 \
		$(BACKEND_IMAGE)
	@echo "✓ Backend corriendo en http://localhost:8080"

stop-docker: ## Detiene y elimina contenedor del backend
	@echo "Deteniendo contenedor..."
	-$(DOCKER) stop edge-cache-backend
	-$(DOCKER) rm edge-cache-backend
	@echo "✓ Contenedor detenido"

pack: build ## Empaqueta la aplicación (crea imagen Docker)
	@echo "Empaquetando aplicación..."
	$(DOCKER) save $(BACKEND_IMAGE) -o edge-cache-backend.tar
	@echo "✓ Imagen guardada en edge-cache-backend.tar"

clean: ## Limpia archivos generados y caché
	@echo "Limpiando..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage
	rm -rf dist build
	@echo "✓ Limpieza completada"

# Comandos Terraform
tf-init: ## Inicializa Terraform
	@echo "Inicializando Terraform..."
	cd $(INFRA_DIR) && $(TERRAFORM) init
	@echo "✓ Terraform inicializado"

tf-validate: tf-init ## Valida configuración de Terraform
	@echo "Validando Terraform..."
	cd $(INFRA_DIR) && $(TERRAFORM) validate
	cd $(INFRA_DIR) && $(TERRAFORM) fmt -check -recursive
	@echo "✓ Validación completada"

tf-lint: ## Ejecuta tflint
	@echo "Ejecutando tflint..."
	cd $(INFRA_DIR) && tflint --init
	cd $(INFRA_DIR) && tflint
	@echo "✓ tflint completado"

tf-sec: ## Ejecuta tfsec (análisis de seguridad)
	@echo "Ejecutando tfsec..."
	cd $(INFRA_DIR) && tfsec .
	@echo "✓ tfsec completado"

plan: tf-validate ## Genera plan de Terraform
	@echo "Generando plan de Terraform..."
	cd $(INFRA_DIR) && $(TERRAFORM) plan -out=tfplan
	@echo "✓ Plan generado: $(INFRA_DIR)/tfplan"

apply: plan ## Aplica infraestructura con Terraform
	@echo "Aplicando infraestructura..."
	cd $(INFRA_DIR) && $(TERRAFORM) apply tfplan
	@echo "✓ Infraestructura desplegada"
	@echo ""
	@echo "Servicios disponibles:"
	@echo "  Backend: http://localhost:8080"
	@echo "  Proxy:   http://localhost:80"

destroy: ## Destruye infraestructura
	@echo "Destruyendo infraestructura..."
	cd $(INFRA_DIR) && $(TERRAFORM) destroy -auto-approve
	@echo "✓ Infraestructura destruida"

tf-drift: ## Verifica drift de infraestructura
	@echo "Verificando drift..."
	cd $(INFRA_DIR) && $(TERRAFORM) plan -detailed-exitcode || \
		(echo "⚠️  Drift detectado" && exit 0)
	@echo "✓ Sin drift detectado"

# Comandos de desarrollo completo
dev-setup: tools tf-init ## Setup completo de desarrollo
	@echo "✓ Entorno de desarrollo configurado"

dev-up: apply ## Levanta entorno completo
	@echo "✓ Entorno levantado"

dev-down: destroy stop-docker ## Detiene entorno completo
	@echo "✓ Entorno detenido"

# CI checks (lo que se ejecuta en CI/CD)
ci-lint: lint format-check ## Verifica código (CI)
	@echo "✓ CI lint checks passed"

ci-test: test coverage ## Ejecuta tests con cobertura (CI)
	@echo "✓ CI tests passed"

ci-security: tf-sec ## Ejecuta checks de seguridad (CI)
	@echo "✓ CI security checks passed"

ci-iac: tf-validate tf-lint plan ## Valida IaC (CI)
	@echo "✓ CI IaC checks passed"

ci-all: ci-lint ci-test ci-security ci-iac ## Ejecuta todos los checks de CI
	@echo "✓ All CI checks passed"

# Comandos de métricas
metrics: ## Analiza logs y genera reporte de métricas
	@echo "Analizando métricas..."
	$(PYTHON) scripts/analyze_logs.py --container edge-cache-proxy
	@echo "✓ Análisis completado"

report: ## Genera reporte de performance
	@echo "Generando reporte..."
	$(PYTHON) scripts/generate_report.py
	@echo "✓ Reporte generado"

# Comandos de logs
logs-backend: ## Muestra logs del backend
	$(DOCKER) logs -f edge-cache-backend

logs-proxy: ## Muestra logs del proxy
	$(DOCKER) logs -f edge-cache-proxy

# Smoke tests
smoke: ## Ejecuta smoke tests contra el entorno
	@echo "Ejecutando smoke tests..."
	@curl -f http://localhost:80/health || (echo "❌ Health check failed" && exit 1)
	@curl -f http://localhost:80/api/static || (echo "❌ Static endpoint failed" && exit 1)
	@curl -f http://localhost:80/api/dynamic || (echo "❌ Dynamic endpoint failed" && exit 1)
	@echo "✓ Smoke tests passed"