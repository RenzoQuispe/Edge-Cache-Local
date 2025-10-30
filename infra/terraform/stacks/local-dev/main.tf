# Stack de desarrollo local - Patrón Composite
# Orquesta backend + proxy + monitor en una red local

terraform {
  required_version = ">= 1.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

# Provider de Docker
provider "docker" {
  host = "unix:///var/run/docker.sock"
}

# Red local para comunicación entre servicios
resource "docker_network" "edge_cache" {
  name   = var.network_name
  driver = "bridge"

  ipam_config {
    subnet  = "172.20.0.0/16"
    gateway = "172.20.0.1"
  }

  labels {
    label = "project"
    value = "edge-cache-local"
  }
}

# Módulo Backend
module "backend" {
  source = "../../modules/backend"

  container_name = var.backend_container_name
  image_name     = var.backend_image
  build_context  = var.backend_build_context

  internal_port = var.backend_internal_port
  external_port = var.backend_external_port

  network_name = docker_network.edge_cache.name

  environment = merge(
    var.backend_environment,
    {
      BACKEND_PORT = tostring(var.backend_internal_port)
      APP_VERSION  = var.app_version
    }
  )

  restart_policy = var.restart_policy
  app_version    = var.app_version
}

# Módulo Proxy
module "proxy" {
  source = "../../modules/proxy"

  container_name    = var.proxy_container_name
  nginx_image       = var.nginx_image
  nginx_config_path = var.nginx_config_path

  external_port = var.proxy_external_port
  network_name  = docker_network.edge_cache.name

  restart_policy = var.restart_policy

  # Dependencia explícita del backend
  backend_container_id = module.backend.container_id
}

# Módulo Monitor (contenedor simple para métricas)
module "monitor" {
  source = "../../modules/monitor"

  container_name = var.monitor_container_name
  network_name   = docker_network.edge_cache.name

  logs_volume_name = module.proxy.logs_volume

  restart_policy = var.restart_policy
}

# Outputs del stack completo
output "network_id" {
  description = "ID de la red Docker"
  value       = docker_network.edge_cache.id
}

output "backend_endpoint" {
  description = "Endpoint del backend"
  value       = module.backend.external_endpoint
}

output "proxy_endpoint" {
  description = "Endpoint del proxy (punto de entrada principal)"
  value       = module.proxy.proxy_endpoint
}

output "monitor_container" {
  description = "Nombre del contenedor de monitoreo"
  value       = module.monitor.container_name
}

output "stack_summary" {
  description = "Resumen del stack desplegado"
  value = {
    network        = docker_network.edge_cache.name
    backend        = module.backend.container_name
    proxy          = module.proxy.container_name
    monitor        = module.monitor.container_name
    app_version    = var.app_version
    proxy_url      = module.proxy.proxy_endpoint
    backend_direct = module.backend.external_endpoint
  }
}

# Data source para validar que no hay drift
data "docker_network" "validation" {
  name = docker_network.edge_cache.name

  depends_on = [docker_network.edge_cache]
}