.PHONY: help start stop test migrate venv install clean test-stop

# Переменные
PYTHON := python3
VENV := venv
VENV_BIN := $(VENV)/bin
VENV_ACTIVATE := $(VENV_BIN)/activate
DOCKER_COMPOSE := docker-compose
TEST_RABBIT_CONTAINER := test_rabbit
TEST_POSTGRES_CONTAINER := test_postgres

help: ## Показать справку по командам
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

start: ## Собрать и запустить все сервисы в фоне
	@echo "Building Docker images..."
	$(DOCKER_COMPOSE) build
	@echo "Starting services..."
	$(DOCKER_COMPOSE) up -d
	@echo "Services started. Use 'make stop' to stop them."

stop: ## Остановить все сервисы
	@echo "Stopping services..."
	$(DOCKER_COMPOSE) down
	@echo "Services stopped."

test-stop: ## Остановить тестовые контейнеры
	@echo "Stopping test containers..."
	@docker stop $(TEST_RABBIT_CONTAINER) 2>/dev/null || true
	@docker stop $(TEST_POSTGRES_CONTAINER) 2>/dev/null || true
	@docker rm $(TEST_RABBIT_CONTAINER) 2>/dev/null || true
	@docker rm $(TEST_POSTGRES_CONTAINER) 2>/dev/null || true
	@echo "Test containers stopped and removed."

test: test-stop ## Запустить тесты с тестовыми контейнерами
	@echo "Starting test containers..."
	@docker run -d --name $(TEST_POSTGRES_CONTAINER) \
		-e POSTGRES_USER=test_user \
		-e POSTGRES_PASSWORD=test_password \
		-e POSTGRES_DB=test_db \
		-p 5434:5432 \
		postgres:15-alpine
	@docker run -d --name $(TEST_RABBIT_CONTAINER) \
		-e RABBITMQ_DEFAULT_USER=test_user \
		-e RABBITMQ_DEFAULT_PASS=test_password \
		-p 5673:5672 \
		-p 15673:15672 \
		rabbitmq:3.12-management-alpine
	@echo "Waiting for test containers to be ready..."
	@sleep 5
	@echo "Running tests for service-orders..."
	@cd service-orders && $(MAKE) test-local || (cd .. && $(MAKE) test-stop && exit 1)
	@echo "Running tests for service-processor..."
	@cd service-processor && $(MAKE) test-local || (cd .. && $(MAKE) test-stop && exit 1)
	@$(MAKE) test-stop
	@echo "All tests completed successfully!"

migrate: ## Применить миграции для обоих сервисов
	@echo "Running migrations for service-orders..."
	@cd service-orders && alembic upgrade head
	@echo "Running migrations for service-processor..."
	@cd service-processor && alembic upgrade head
	@echo "Migrations completed."

migrate-orders: ## Применить миграции только для service-orders
	@echo "Running migrations for service-orders..."
	@cd service-orders && alembic upgrade head

migrate-processor: ## Применить миграции только для service-processor
	@echo "Running migrations for service-processor..."
	@cd service-processor && alembic upgrade head

venv: ## Создать виртуальное окружение
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV); \
		echo "Virtual environment created."; \
	else \
		echo "Virtual environment already exists."; \
	fi
	@echo "To activate virtual environment, run:"
	@echo "  source $(VENV_ACTIVATE)  # Linux/Mac"
	@echo "  $(VENV_BIN)\activate     # Windows"

install: venv ## Установить все зависимости
	@echo "Installing dependencies for service-orders..."
	@cd service-orders && ../$(VENV_BIN)/pip install --upgrade pip setuptools wheel && ../$(VENV_BIN)/pip install -e ".[test]"
	@echo "Installing dependencies for service-processor..."
	@cd service-processor && ../$(VENV_BIN)/pip install --upgrade pip setuptools wheel && ../$(VENV_BIN)/pip install -e ".[test]"
	@echo "All dependencies installed."

install-orders: venv ## Установить зависимости только для service-orders
	@echo "Installing dependencies for service-orders..."
	@cd service-orders && ../$(VENV_BIN)/pip install --upgrade pip setuptools wheel && ../$(VENV_BIN)/pip install -e ".[test]"

install-processor: venv ## Установить зависимости только для service-processor
	@echo "Installing dependencies for service-processor..."
	@cd service-processor && ../$(VENV_BIN)/pip install --upgrade pip setuptools wheel && ../$(VENV_BIN)/pip install -e ".[test]"

clean: ## Очистить временные файлы и контейнеры
	@echo "Cleaning up..."
	@$(MAKE) test-stop
	@docker-compose down -v 2>/dev/null || true
	@find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	@echo "Cleanup completed."

logs: ## Показать логи всех сервисов
	$(DOCKER_COMPOSE) logs -f

logs-orders: ## Показать логи service-orders
	$(DOCKER_COMPOSE) logs -f service-orders

logs-processor: ## Показать логи service-processor
	$(DOCKER_COMPOSE) logs -f service-processor

restart: stop start ## Перезапустить все сервисы

rebuild: stop ## Пересобрать и запустить все сервисы
	$(DOCKER_COMPOSE) build --no-cache
	$(DOCKER_COMPOSE) up -d
