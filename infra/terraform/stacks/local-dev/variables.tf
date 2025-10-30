# Variables del stack local-dev

# General
variable "app_version" {
  description = "Versión de la aplicación"
  type        = string
  default     = "1.0.0"
}

variable "network_name" {
  description = "Nombre de la red Docker"
  type        = string
  default     = "edge-cache-network"
}

variable "restart_policy" {
  description = "Política de reinicio para todos los contenedores"
  type        = string
  default     = "unless-stopped"
}

# Backend
variable "backend_container_name" {
  description = "Nombre del contenedor backend"
  type        = string
  default     = "backend"
}

variable "backend_image" {
  description = "Imagen Docker del backend"
  type        = string
  default     = "edge-cache-backend:latest"
}

variable "backend_build_context" {
  description = "Contexto de build del backend (vacío para usar imagen existente)"
  type        = string
  default     = "../../../../"
}

variable "backend_internal_port" {
  description = "Puerto interno del backend"
  type        = number
  default     = 8080
}

variable "backend_external_port" {
  description = "Puerto externo del backend"
  type        = number
  default     = 8080
}

variable "backend_environment" {
  description = "Variables de entorno del backend"
  type        = map(string)
  default = {
    FLASK_DEBUG  = "false"
    LOG_LEVEL    = "INFO"
    BACKEND_HOST = "0.0.0.0"
  }
}

# Proxy
variable "proxy_container_name" {
  description = "Nombre del contenedor proxy"
  type        = string
  default     = "edge-cache-proxy"
}

variable "nginx_image" {
  description = "Imagen de Nginx"
  type        = string
  default     = "nginx:alpine"
}

variable "nginx_config_path" {
  description = "Path a la configuración de Nginx"
  type        = string
  default     = "../../../../proxy/nginx.conf"
}

variable "proxy_external_port" {
  description = "Puerto externo del proxy"
  type        = number
  default     = 80
}

# Monitor
variable "monitor_container_name" {
  description = "Nombre del contenedor de monitoreo"
  type        = string
  default     = "edge-cache-monitor"
}