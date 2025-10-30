# Variables del módulo proxy

variable "nginx_image" {
  description = "Imagen de Nginx a usar"
  type        = string
  default     = "nginx:alpine"
}

variable "container_name" {
  description = "Nombre del contenedor proxy"
  type        = string
  default     = "edge-cache-proxy"
}

variable "external_port" {
  description = "Puerto expuesto del proxy"
  type        = number
  default     = 80
  
  validation {
    condition     = var.external_port > 0 && var.external_port <= 65535
    error_message = "El puerto debe estar entre 1 y 65535."
  }
}

variable "nginx_config_path" {
  description = "Path a la configuración de Nginx en el host"
  type        = string
  default     = "./proxy/nginx.conf"
}

variable "network_name" {
  description = "Nombre de la red Docker"
  type        = string
  default     = "edge-cache-network"
}

variable "restart_policy" {
  description = "Política de reinicio"
  type        = string
  default     = "unless-stopped"
}

variable "environment" {
  description = "Variables de entorno"
  type        = map(string)
  default     = {}
}

variable "healthcheck_interval" {
  description = "Intervalo de health checks"
  type        = string
  default     = "30s"
}

variable "healthcheck_timeout" {
  description = "Timeout del health check"
  type        = string
  default     = "5s"
}

variable "healthcheck_retries" {
  description = "Reintentos del health check"
  type        = number
  default     = 3
}

variable "backend_container_id" {
  description = "ID del contenedor backend (dependencia)"
  type        = string
  default     = ""
}