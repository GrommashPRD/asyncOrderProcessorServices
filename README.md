# README

## Описание.
Асинхронные сервисы создания и обработки заказов

1. Язык программирования: Python 3.11
2. База данных: PostgreSQL 17
3. Брокер сообщений: RabbitMQ
4. Основной фреймворк: FastAPI
5. ORM: SQLAlchemy
6. Система миграций: Alembic

Для обеспечения согласованности и идемпотентности данных реализован паттерн Transactional Outbox. \
Логика удачной или неудачной обрабюотки заказов случайна. Никакой конкретной логики подсчета суммы заказа или подсчета стоимости за единицу товара \
в приложении не реализовано. Для этого лишь подготовлен "фундамент".

## Управление и запуск.

### `make start`
Собирает Docker образы и запускает все сервисы в фоновом режиме:
```bash
make start
```

### `make stop`
Останавливает все запущенные сервисы:
```bash
make stop
```

### `make test`
Останавливает существующие тестовые контейнеры (если есть), запускает новые тестовые контейнеры с PostgreSQL и RabbitMQ, затем прогоняет тесты для обоих сервисов:
```bash
make test
```
**Примечание:** Тесты используют моки и не требуют реальных контейнеров, но команда создает их для полноты тестирования. \
Запускайте тесты после установки всех зависимостей(make venv и make install)

### `make migrate`
Применяет миграции для обоих сервисов (service-orders и service-processor):
```bash
make migrate
```

Также доступны отдельные команды:
- `make migrate-orders` - миграции только для service-orders
- `make migrate-processor` - миграции только для service-processor

### `make venv`
Создает виртуальное окружение Python в корне проекта:
```bash
make venv
```

После создания активируйте его:
- Linux/Mac: `source venv/bin/activate`
- Windows: `venv\bin\activate`

### `make install`
Создает виртуальное окружение (если его нет) и устанавливает все зависимости для обоих сервисов:
```bash
make install
```

## Дополнительные команды

### `make clean`
Очищает временные файлы, контейнеры и volumes:
```bash
make clean
```

### `make logs`
Показывает логи всех сервисов:
```bash
make logs
```

### `make logs-orders`
Показывает логи только service-orders:
```bash
make logs-orders
```

### `make logs-processor`
Показывает логи только service-processor:
```bash
make logs-processor
```

### `make restart`
Останавливает и заново запускает все сервисы:
```bash
make restart
```

### `make rebuild`
Останавливает сервисы, пересобирает образы без кэша и запускает заново:
```bash
make rebuild
```

### `make help`
Показывает справку по всем доступным командам:
```bash
make help
```


# Примеры использования

### Первый запуск проекта:
```bash
# Создать виртуальное окружение и установить зависимости
make install

# Запустить все сервисы
make start

# Применить миграции (если нужно)
make migrate
```

### Запуск тестов:
```bash
# Установите все зависимости
make install

# Запустите тесты
make test
```

### Остановка проекта:
```bash
make stop
```

# Примеры запросов.
1. Создание заказа. Отдельной логики user'ов, product'ов нет, т.к не было в задании. \
Поэтому все значения(user_id, products, amount) пишутся ручками.

```
curl -X 'POST' \
  'http://localhost:8000/api/v1/orders/new/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "user_id": "user_1",
  "products": [
    {
      "product_id": "product_001",
      "quantity": 1
    },
    {
      "product_id": "product_002",
      "quantity": 19
    },
    {
      "product_id": "product_003",
      "quantity": 17
    }
  ],
  "amount": "140"
}'
```

2. Получение статуса заказа. \
order_id из пункта выше.

```
curl -X 'GET' \
  'http://localhost:8000/api/v1/orders/<ORDER_ID>/status' \
  -H 'accept: application/json'
```
