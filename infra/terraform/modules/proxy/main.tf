# Módulo Terraform para Nginx proxy con caché

terraform {
  required_version = ">= 1.0"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

# Imagen de Nginx
resource "docker_image" "nginx" {
  name = var.nginx_image
}

# Volumen para caché de Nginx
resource "docker_volume" "cache" {
  name = "${var.container_name}-cache"
}

# Volumen para logs
resource "docker_volume" "logs" {
  name = "${var.container_name}-logs"
}

# Contenedor de Nginx
resource "docker_container" "proxy" {
  name  = var.container_name
  image = docker_image.nginx.image_id
  
  restart = var.restart_policy
  
  # Puerto HTTP
  ports {
    internal = 80
    external = var.external_port
    protocol = "tcp"
  }
  
  # Montar configuración de Nginx
  volumes {
    host_path      = var.nginx_config_path
    container_path = "/etc/nginx/nginx.conf"
    read_only      = true
  }
  
  # Volumen para caché
  volumes {
    volume_name    = docker_volume.cache.name
    container_path = "/var/cache/nginx"
  }
  
  # Volumen para logs
  volumes {
    volume_name    = docker_volume.logs.name
    container_path = "/var/log/nginx"
  }
  
  # Variables de entorno
  env = [
    for key, value in var.environment : "${key}=${value}"
  ]
  
  # Health check
  healthcheck {
    test     = ["CMD", "curl", "-f", "http://localhost/proxy/health"]
    interval = var.healthcheck_interval
    timeout  = var.healthcheck_timeout
    retries  = var.healthcheck_retries
  }
  
  # Logs
  log_driver = "json-file"
  log_opts = {
    max-size = "10m"
    max-file = "3"
  }
  
  # Red
  networks_advanced {
    name = var.network_name
  }
  
  # Labels
  labels {
    label = "app"
    value = "edge-cache-proxy"
  }
  
  labels {
    label = "module"
    value = "terraform-proxy"
  }
  
  # Dependencia: esperar a que el backend esté listo
  depends_on = [var.backend_container_id]
}

# Outputs
output "container_id" {
  description = "ID del contenedor proxy"
  value       = docker_container.proxy.id
}

output "container_name" {
  description = "Nombre del contenedor"
  value       = docker_container.proxy.name
}

output "proxy_endpoint" {
  description = "Endpoint del proxy"
  value       = "http://localhost:${var.external_port}"
}

output "cache_volume" {
  description = "Nombre del volumen de caché"
  value       = docker_volume.cache.name
}

output "logs_volume" {
  description = "Nombre del volumen de logs"
  value       = docker_volume.logs.name
}