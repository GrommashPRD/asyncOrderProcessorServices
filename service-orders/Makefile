.PHONY: test-local

VENV := ../venv
VENV_BIN := $(VENV)/bin
PYTEST := $(VENV_BIN)/pytest

test-local: ## Запустить тесты локально (используется из корневого Makefile)
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Run 'make install' from project root first."; \
		exit 1; \
	fi
	@echo "Running tests for service-orders..."
	@DB_HOST=localhost DB_PORT=5434 DB_NAME=test_db DB_USER=test_user DB_PASS=test_password \
	RABBIT_HOST=localhost RABBIT_PORT=5673 RABBIT_USER=test_user RABBIT_PASS=test_password \
	$(PYTEST) -v || exit 1
