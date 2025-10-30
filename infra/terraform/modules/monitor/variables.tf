# Variables del módulo monitor

variable "monitor_image" {
  description = "Imagen base para el monitor"
  type        = string
  default     = "python:3.11-alpine"
}

variable "container_name" {
  description = "Nombre del contenedor"
  type        = string
  default     = "edge-cache-monitor"
}

variable "network_name" {
  description = "Nombre de la red Docker"
  type        = string
}

variable "logs_volume_name" {
  description = "Nombre del volumen de logs a monitorear"
  type        = string
}

variable "restart_policy" {
  description = "Política de reinicio"
  type        = string
  default     = "unless-stopped"
}

variable "metrics_port" {
  description = "Puerto interno para métricas"
  type        = number
  default     = 9090
}

variable "metrics_external_port" {
  description = "Puerto externo para métricas"
  type        = number
  default     = 9090
}

variable "scrape_interval" {
  description = "Intervalo de scraping en segundos"
  type        = number
  default     = 60
}