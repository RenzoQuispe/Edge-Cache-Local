# Módulo Monitor - Contenedor simple para analizar logs y generar métricas

terraform {
  required_version = ">= 1.0"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

# Imagen Python para el monitor
resource "docker_image" "monitor" {
  name = var.monitor_image
}

# Contenedor del monitor
resource "docker_container" "monitor" {
  name  = var.container_name
  image = docker_image.monitor.image_id
  
  restart = var.restart_policy
  
  # Puerto para métricas (opcional)
  ports {
    internal = var.metrics_port
    external = var.metrics_external_port
    protocol = "tcp"
  }
  
  # Montar volumen de logs del proxy
  volumes {
    volume_name    = var.logs_volume_name
    container_path = "/logs"
    read_only      = true
  }
  
  # Comando: analizar logs cada N segundos
  command = [
    "sh", "-c",
    "while true; do python3 /app/analyze_logs.py /logs/access.log; sleep ${var.scrape_interval}; done"
  ]
  
  # Variables de entorno
  env = [
    "METRICS_ENABLED=true",
    "SCRAPE_INTERVAL=${var.scrape_interval}",
    "LOG_FILE=/logs/access.log"
  ]
  
  # Red
  networks_advanced {
    name = var.network_name
  }
  
  # Labels
  labels {
    label = "app"
    value = "edge-cache-monitor"
  }
  
  labels {
    label = "module"
    value = "terraform-monitor"
  }
}

# Outputs
output "container_id" {
  description = "ID del contenedor monitor"
  value       = docker_container.monitor.id
}

output "container_name" {
  description = "Nombre del contenedor"
  value       = docker_container.monitor.name
}

output "metrics_endpoint" {
  description = "Endpoint de métricas"
  value       = "http://localhost:${var.metrics_external_port}/metrics"
}