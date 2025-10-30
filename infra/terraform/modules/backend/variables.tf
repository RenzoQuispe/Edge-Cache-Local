# Variables del módulo backend con defaults sensatos (patrón Factory)

variable "image_name" {
  description = "Nombre de la imagen Docker"
  type        = string
  default     = "edge-cache-backend:latest"
}

variable "container_name" {
  description = "Nombre del contenedor"
  type        = string
  default     = "backend"
}

variable "build_context" {
  description = "Path al contexto de build (si se construye localmente)"
  type        = string
  default     = ""
}

variable "dockerfile" {
  description = "Path al Dockerfile"
  type        = string
  default     = "Dockerfile"
}

variable "internal_port" {
  description = "Puerto interno del contenedor"
  type        = number
  default     = 8080
  
  validation {
    condition     = var.internal_port > 0 && var.internal_port <= 65535
    error_message = "El puerto debe estar entre 1 y 65535."
  }
}

variable "external_port" {
  description = "Puerto expuesto al host"
  type        = number
  default     = 8080
  
  validation {
    condition     = var.external_port > 0 && var.external_port <= 65535
    error_message = "El puerto debe estar entre 1 y 65535."
  }
}

variable "environment" {
  description = "Variables de entorno para el contenedor"
  type        = map(string)
  default = {
    BACKEND_HOST  = "0.0.0.0"
    BACKEND_PORT  = "8080"
    FLASK_DEBUG   = "false"
    APP_VERSION   = "1.0.0"
    LOG_LEVEL     = "INFO"
  }
}

variable "network_name" {
  description = "Nombre de la red Docker"
  type        = string
  default     = "edge-cache-network"
}

variable "restart_policy" {
  description = "Política de reinicio del contenedor"
  type        = string
  default     = "unless-stopped"
  
  validation {
    condition     = contains(["no", "always", "on-failure", "unless-stopped"], var.restart_policy)
    error_message = "Política de reinicio debe ser: no, always, on-failure, o unless-stopped."
  }
}

variable "app_version" {
  description = "Versión de la aplicación"
  type        = string
  default     = "1.0.0"
}

variable "healthcheck_interval" {
  description = "Intervalo entre health checks"
  type        = string
  default     = "30s"
}

variable "healthcheck_timeout" {
  description = "Timeout del health check"
  type        = string
  default     = "5s"
}

variable "healthcheck_retries" {
  description = "Número de reintentos del health check"
  type        = number
  default     = 3
  
  validation {
    condition     = var.healthcheck_retries > 0 && var.healthcheck_retries <= 10
    error_message = "Retries debe estar entre 1 y 10."
  }
}