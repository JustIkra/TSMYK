# ЦМУК — Цифровая модель универсальных компетенций

Автоматизированная платформа для оценки профессиональной пригодности кандидатов на основе анализа психометрических отчётов.

## Решаемая проблема

Оценка профессиональной пригодности требует анализа комплексных психометрических отчётов с множеством метрик компетенций. Данные представлены в виде визуальных элементов (таблицы, графики), что делает ручное извлечение трудоёмким и немасштабируемым. Отсутствие единой методологии приводит к субъективности оценок.

**ЦМУК автоматизирует этот процесс:**
- Извлекает данные из визуальных элементов DOCX-документов с помощью Gemini Vision
- Проводит многомерный анализ компетенций
- Рассчитывает коэффициент профессиональной пригодности по адаптивным скоринговым моделям
- Генерирует персонализированные рекомендации

## Целевые пользователи

| Роль | Использование |
|------|---------------|
| **HR-специалисты** | Загрузка отчётов, просмотр результатов оценки кандидатов |
| **Администраторы** | Настройка весовых таблиц для разных профессий, модерация пользователей |
| **Разработчики** | Расширение функционала, интеграция с внешними системами |

## Ключевые сценарии

1. **Загрузка отчёта** — пользователь загружает DOCX с психометрическими данными
2. **Автоматическое извлечение** — система извлекает изображения и через Gemini Vision преобразует их в структурированные метрики
3. **Корректировка** — пользователь проверяет и при необходимости корректирует извлечённые значения
4. **Расчёт оценки** — система применяет весовую модель для выбранной профессии и вычисляет итоговый балл
5. **Отчёт** — генерируется итоговый отчёт с оценкой, сильными сторонами, зонами развития и рекомендациями

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│                   Vue 3 + Vite + Pinia                       │
│                   (SPA, baseURL=/api)                        │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP
┌─────────────────────────▼───────────────────────────────────┐
│                      api-gateway                             │
│            FastAPI (REST API + SPA serving)                  │
│                     порт 9187                                │
└──────┬────────────────────────────────────┬─────────────────┘
       │                                    │
       │ SQL                                │ AMQP
       ▼                                    ▼
┌──────────────┐                    ┌───────────────┐
│ PostgreSQL   │                    │  RabbitMQ     │
│    15        │                    │    3.13       │
└──────────────┘                    └───────┬───────┘
                                            │
                           ┌────────────────┼────────────────┐
                           │                │                │
                           ▼                ▼                ▼
                    ┌───────────┐    ┌───────────┐    ┌───────────┐
                    │  worker   │    │  worker-  │    │   Redis   │
                    │(extraction)│   │recomm.    │    │     7     │
                    └─────┬─────┘    └─────┬─────┘    └───────────┘
                          │                │
                          └────────┬───────┘
                                   │ HTTPS (через VPN)
                                   ▼
                           ┌───────────────┐
                           │  Gemini API   │
                           │   (Vision)    │
                           └───────────────┘
```

### Компоненты

| Компонент | Описание |
|-----------|----------|
| **frontend** | Vue 3 SPA (Composition API), Element Plus, Pinia |
| **api-gateway** | FastAPI backend, REST API, отдача SPA |
| **worker** | Celery worker для извлечения метрик из DOCX через Gemini Vision |
| **worker-recommendations** | Celery worker для генерации текстовых рекомендаций |
| **PostgreSQL** | Основная БД (метрики, пользователи, результаты) |
| **Redis** | Кэш и брокер результатов Celery |
| **RabbitMQ** | Брокер задач Celery |

## Быстрый старт

### Требования

- Docker и Docker Compose
- (опционально) Node.js 18+ и npm для разработки фронтенда
- (опционально) Python 3.11+ для локальной разработки бэкенда

### Запуск через Docker Compose

```bash
# 1. Клонируйте репозиторий
git clone <repo-url>
cd rksi_hack

# 2. Создайте .env на основе примера
cp .env.example .env
# Отредактируйте .env: укажите GEMINI_API_KEYS и JWT_SECRET

# 3. Соберите и запустите
docker-compose build
docker-compose up -d

# 4. Примените миграции (выполняется автоматически, но можно вручную)
docker-compose exec app alembic upgrade head

# 5. Создайте администратора
docker-compose exec app python create_admin.py admin@example.com yourpassword

# 6. Откройте в браузере
open http://localhost:9187
```

### Локальная разработка

**Backend:**
```bash
cd api-gateway
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Настройте .env в корне проекта
alembic upgrade head
python setup_test_data.py  # опционально, начальные данные

uvicorn main:app --reload --port 9187
```

**Celery worker:**
```bash
cd api-gateway
celery -A app.core.celery_app.celery_app worker -l info
```

**Frontend:**
```bash
cd frontend
npm install

# Сборка для production (результат в api-gateway/static/)
npm run build

# Или hot-reload режим
VITE_API_TARGET=http://localhost:9187 npm run dev
# Доступен по http://localhost:5173
```

### Тестирование

```bash
cd api-gateway

pytest                              # все тесты
pytest -m unit                      # только unit-тесты
pytest -m integration               # интеграционные (нужна БД)
pytest --cov=app --cov-report=html  # с покрытием
```

## Конфигурация

Единый файл `.env` в корне проекта. Ключевые переменные:

| Переменная | Описание | Пример |
|------------|----------|--------|
| `APP_PORT` | Порт приложения | `9187` |
| `ENV` | Профиль окружения | `dev`, `test`, `ci`, `prod` |
| `JWT_SECRET` | Секрет для JWT токенов (мин. 32 символа) | `openssl rand -hex 32` |
| `POSTGRES_DSN` | Строка подключения к PostgreSQL | `postgresql+asyncpg://app:app@postgres:5432/app` |
| `REDIS_URL` | URL Redis | `redis://redis:6379/0` |
| `RABBITMQ_URL` | URL RabbitMQ | `amqp://guest:guest@rabbitmq:5672//` |
| `GEMINI_API_KEYS` | API ключи Gemini (через запятую) | `key1,key2,key3` |
| `AI_RECOMMENDATIONS_ENABLED` | Включить генерацию рекомендаций | `1` |
| `VPN_ENABLED` | Использовать VPN для доступа к Gemini | `0` или `1` |

Полный список переменных см. в `.env.example`.

## Структура репозитория

```
├── api-gateway/           # FastAPI backend
│   ├── app/
│   │   ├── core/          # Конфигурация, Celery, middleware
│   │   ├── db/            # SQLAlchemy модели, сессии
│   │   ├── routers/       # API endpoints
│   │   ├── services/      # Бизнес-логика
│   │   ├── repositories/  # Слой доступа к данным
│   │   ├── schemas/       # Pydantic DTO
│   │   └── tasks/         # Celery tasks
│   ├── static/            # Сборка frontend (из frontend/dist)
│   └── tests/             # Pytest тесты
├── frontend/              # Vue 3 SPA
│   ├── src/
│   │   ├── api/           # Axios клиент
│   │   ├── views/         # Страницы
│   │   ├── stores/        # Pinia stores
│   │   └── router/        # Vue Router
│   └── vite.config.js
├── .memory-base/          # Документация
│   ├── busnes-logic/      # Бизнес-требования
│   └── tech-docs/         # Техническая документация
├── docker-compose.yml
└── .env.example           # Шаблон конфигурации
```

## Документация

| Документ | Описание |
|----------|----------|
| [`.memory-base/busnes-logic/business-requirements.md`](.memory-base/busnes-logic/business-requirements.md) | Бизнес-требования и описание проблемы |
| [`.memory-base/tech-docs/architecture.md`](.memory-base/tech-docs/architecture.md) | Архитектура системы |
| [`.memory-base/tech-docs/data-model.md`](.memory-base/tech-docs/data-model.md) | Модель данных (БД) |
| [`.memory-base/tech-docs/api.md`](.memory-base/tech-docs/api.md) | Описание REST API |
| [`CLAUDE.md`](CLAUDE.md) | Инструкции для Claude Code |

## Формула расчёта

Коэффициент профессиональной пригодности:

```
score_pct = Σ(value × weight) × 10
```

где:
- `value` — значение метрики (1–10)
- `weight` — вес метрики для выбранной профессии (сумма весов = 1.0)
- Результат: 0–100%

## Технологический стек

**Backend:**
- FastAPI, SQLAlchemy 2 (async), Alembic
- Pydantic v2, Celery
- PostgreSQL 15, Redis 7, RabbitMQ 3.13

**Frontend:**
- Vue 3 (Composition API), Vite
- Pinia, Element Plus, Axios

**AI:**
- Gemini API (gemini-2.5-flash) для Vision и генерации текста

## Лицензия

См. файл [LICENSE](LICENSE).
