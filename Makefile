# ════════════════════════════════════════════════════════════════════════════
#  MAKEFILE — Comandos Docker Útiles
#  Sistema de Control de Ingresos SENA
# ════════════════════════════════════════════════════════════════════════════

.PHONY: help build up down logs clean status shell-api shell-db

# Colores para output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Mostrar esta ayuda
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║   DOCKER SENA - Sistema de Control de Ingresos Aprendices  ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Ejemplo:$(NC)"
	@echo "  make build          # Construir imagen Docker"
	@echo "  make up             # Iniciar servicios"
	@echo "  make logs-api       # Ver logs del backend"
	@echo ""

setup: ## Configurar archivo .env
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)Creando archivo .env...$(NC)"; \
		cp .env.docker .env; \
		echo "$(GREEN)✓ Archivo .env creado.$(NC)"; \
		echo "$(YELLOW)Por favor edita los valores en .env antes de continuar.$(NC)"; \
	else \
		echo "$(GREEN)✓ Archivo .env ya existe.$(NC)"; \
	fi

build: ## Construir imagen Docker (reconstruir después de cambios en requirements.txt)
	@echo "$(BLUE)Construyendo imagen Docker...$(NC)"
	docker-compose build --no-cache

build-fast: ## Construir imagen Docker (sin cache)
	@echo "$(BLUE)Construyendo imagen Docker (modo rápido)...$(NC)"
	docker-compose build

up: ## Iniciar todos los servicios (detach mode)
	@echo "$(BLUE)Iniciando servicios...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Servicios iniciados.$(NC)"
	@echo ""
	@echo "$(YELLOW)Acceso:$(NC)"
	@echo "  Frontend:  http://localhost"
	@echo "  Backend:   http://localhost:8000"
	@echo "  PostgreSQL: localhost:5432"
	@echo ""

up-debug: ## Iniciar servicios en modo debug (logs en consola)
	@echo "$(BLUE)Iniciando servicios en modo debug...$(NC)"
	docker-compose up

down: ## Detener servicios
	@echo "$(BLUE)Deteniendo servicios...$(NC)"
	docker-compose down

stop: ## Parar servicios sin eliminar volúmenes
	@echo "$(BLUE)Parando servicios...$(NC)"
	docker-compose stop

start: ## Reiniciar servicios detenidos
	@echo "$(BLUE)Reiniciando servicios...$(NC)"
	docker-compose start

restart: ## Reiniciar todos los servicios
	@echo "$(BLUE)Reiniciando servicios...$(NC)"
	docker-compose restart

clean: ## Eliminar contenedores, imágenes y volúmenes (DESTRUCTIVO)
	@echo "$(RED)⚠ ADVERTENCIA: Esto eliminará TODOS los datos en volúmenes.$(NC)"
	@read -p "¿Estás seguro? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(BLUE)Limpiando...$(NC)"; \
		docker-compose down -v; \
		echo "$(GREEN)✓ Limpieza completada.$(NC)"; \
	else \
		echo "$(YELLOW)Operación cancelada.$(NC)"; \
	fi

status: ## Ver estado de los servicios
	@echo "$(BLUE)Estado de servicios:$(NC)"
	docker-compose ps

logs: ## Ver logs de todos los servicios (últimas 50 líneas)
	docker-compose logs --tail=50 -f

logs-api: ## Ver logs del backend
	docker-compose logs --tail=100 -f api

logs-web: ## Ver logs del frontend (Nginx)
	docker-compose logs --tail=100 -f web

logs-db: ## Ver logs de PostgreSQL
	docker-compose logs --tail=100 -f postgres

logs-redis: ## Ver logs de Redis
	docker-compose logs --tail=100 -f redis

shell-api: ## Acceder a shell del contenedor API
	@echo "$(BLUE)Entrando a contenedor API (escribe 'exit' para salir)...$(NC)"
	docker-compose exec api sh

shell-db: ## Acceder a psql en PostgreSQL
	@echo "$(BLUE)Conectando a PostgreSQL (escribe '\\q' para salir)...$(NC)"
	docker-compose exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}

shell-redis: ## Acceder a redis-cli
	@echo "$(BLUE)Conectando a Redis (escribe 'exit' para salir)...$(NC)"
	docker-compose exec redis redis-cli -a ${REDIS_PASSWORD}

shell-web: ## Acceder a shell del contenedor Nginx
	@echo "$(BLUE)Entrando a contenedor Nginx (escribe 'exit' para salir)...$(NC)"
	docker-compose exec web sh

migrate: ## Ejecutar migraciones de base de datos
	@echo "$(BLUE)Ejecutando migraciones...$(NC)"
	docker-compose exec api python -m flask db upgrade

seed: ## Llenar base de datos con datos de ejemplo
	@echo "$(BLUE)Sembrando base de datos...$(NC)"
	docker-compose exec api python backend/populate_data.py

test: ## Ejecutar pruebas unitarias
	@echo "$(BLUE)Ejecutando pruebas...$(NC)"
	docker-compose exec api python -m pytest tests/

health: ## Verificar salud de todos los servicios
	@echo "$(BLUE)Verificando salud de servicios...$(NC)"
	@docker-compose exec api curl -f http://localhost:8000/health && echo "$(GREEN)✓ API: OK$(NC)" || echo "$(RED)✗ API: ERROR$(NC)"
	@docker-compose exec web wget --quiet --tries=1 --spider http://localhost/health && echo "$(GREEN)✓ Web: OK$(NC)" || echo "$(RED)✗ Web: ERROR$(NC)"
	@docker-compose exec postgres pg_isready -U ${POSTGRES_USER} && echo "$(GREEN)✓ PostgreSQL: OK$(NC)" || echo "$(RED)✗ PostgreSQL: ERROR$(NC)"
	@docker-compose exec redis redis-cli -a ${REDIS_PASSWORD} ping && echo "$(GREEN)✓ Redis: OK$(NC)" || echo "$(RED)✗ Redis: ERROR$(NC)"

backup: ## Hacer backup de la base de datos
	@echo "$(BLUE)Haciendo backup de PostgreSQL...$(NC)"
	docker-compose exec postgres pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✓ Backup completado.$(NC)"

restore: ## Restaurar base de datos (especificar SQL_FILE)
	@if [ -z "$(SQL_FILE)" ]; then \
		echo "$(RED)Error: especifica el archivo: make restore SQL_FILE=backup.sql$(NC)"; \
	else \
		echo "$(BLUE)Restaurando base de datos...$(NC)"; \
		cat $(SQL_FILE) | docker-compose exec -T postgres psql -U ${POSTGRES_USER} ${POSTGRES_DB}; \
		echo "$(GREEN)✓ Restauración completada.$(NC)"; \
	fi

prune: ## Limpiar recursos Docker no usados
	@echo "$(BLUE)Limpiando recursos Docker no usados...$(NC)"
	docker system prune -f

versions: ## Mostrar versiones de servicios
	@echo "$(BLUE)Versiones:$(NC)"
	@docker-compose exec api python --version
	@docker-compose exec postgres postgres --version
	@docker-compose exec redis redis-server --version

.DEFAULT_GOAL := help
