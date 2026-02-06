# «Создание REST API на FastApi» — часть 1 и часть 2 (Сервис объявлений)

> Этот README описывает проект **из части 1**, а также доработки **части 2** по заданию (JWT‑авторизация + пользователи + права доступа).

---

## 1) Описание проекта

Сервис объявлений купли/продажи на **FastAPI** с хранением данных в **PostgreSQL** и миграциями **Alembic**.  
Проект полностью **докеризирован** и содержит **автотесты** (pytest + httpx).

**Поля объявления:**
- заголовок (`title`)
- описание (`description`)
- цена (`price`)
- автор (`author`)
- дата создания (`created_at`, выставляется автоматически)
- владелец (`owner_id`, заполняется автоматически из токена, часть 2)

---

## 2) Что добавлено в части 2 (по заданию)

### 2.1 POST `/login` (получение токена)
- Тело запроса: JSON `{ "username": "...", "password": "..." }`
- Ответ: токен (JWT)
- Время жизни токена: **48 часов**
- Неверные креды: **401 Unauthorized**

### 2.2 Роуты управления пользователями (CRUD)
- `POST /user` — создание пользователя
- `GET /user/{user_id}` — получение пользователя по id
- `PATCH /user/{user_id}` — частичное обновление
- `DELETE /user/{user_id}` — удаление

> В задании группы: **user** и **admin**.

### 2.3 Права доступа (строго по формулировке задания)

#### Права неавторизованного пользователя (токен можно не передавать)
- Создание пользователя: `POST /user`
- Получение пользователя по id: `GET /user/{user_id}`
- Получение объявления по id: `GET /advertisement/{advertisement_id}`
- Поиск объявлений: `GET /advertisement?{query_string}`

#### Права авторизованного пользователя группы **user**
- все права неавторизованного
- обновление **своих** данных: `PATCH /user/{user_id}`
- удаление **себя**: `DELETE /user/{user_id}`
- создание объявления: `POST /advertisement`
- обновление **своего** объявления: `PATCH /advertisement/{advertisement_id}`
- удаление **своего** объявления: `DELETE /advertisement/{advertisement_id}`

#### Права авторизованного пользователя группы **admin**
- любые действия с любыми сущностями

#### Ошибка прав
Если у пользователя недостаточно прав — возвращается **403 Forbidden**.

---

## 3) Важное про роль `root` (если у вас она включена)

В вашем проекте дополнительно реализован **bootstrap‑пользователь root через env**, чтобы было удобно “поднять” первого администратора.  

- По смыслу прав доступа **root эквивалентен admin** (может всё).
- **Для выполнения задания наличие `root` не требуется.**
- Если вы хотите строгую реализацию “только user/admin”, просто **не задавайте** переменные `BOOTSTRAP_ROOT_USERNAME/BOOTSTRAP_ROOT_PASSWORD` и **не используйте** группу `root` в запросах/тестах.

> В любом случае, права **admin** полностью соответствуют требованию задания: “любые действия”.

---

## 4) Стек

- Python 3.11
- FastAPI + Uvicorn
- SQLAlchemy (async) + asyncpg
- Alembic (миграции)
- PostgreSQL 16
- JWT (48h)
- Pytest + httpx (ASGITransport)
- Docker / Docker Compose

---

## 5) Структура проекта (часть 2)

```
EX1
├── .env
├── .env.example
├── .env.test
├── .env.test.example
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── main.py
├── pytest.ini
├── requirements.txt
├── test_requests.http
├── alembic
│   ├── env.py
│   └── versions
│       ├── 0001_create_advertisements.py
│       └── 0002_create_users_and_owner_id.py
├── app
│   ├── __init__.py
│   ├── config.py
│   ├── crud.py
│   ├── db.py
│   ├── deps.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── security.py
└── tests
    ├── conftest.py
    ├── test_crud.py
    └── test_search.py
```

### 5.1 Ключевые файлы
- `app/main.py` — FastAPI‑приложение (роуты: /login, /user, /advertisement)
- `app/models.py` — модели SQLAlchemy: `User`, `Advertisement`
- `app/schemas.py` — Pydantic‑схемы входа/выхода
- `app/db.py` — AsyncEngine/Session и dependency `get_db()`
- `app/crud.py` — CRUD для пользователей и объявлений, поиск
- `app/security.py` — хэширование паролей + выпуск JWT
- `app/deps.py` — зависимости авторизации (current_user / optional)
- `alembic/versions/0002_create_users_and_owner_id.py` — таблица users + owner_id в advertisements
- `tests/*` — автотесты (CRUD, search) через httpx ASGITransport

---

## 6) Переменные окружения

Проект использует переменные окружения через `.env` / `.env.test`.

### 6.1 `.env.example` (DEV)
Создайте `.env` на основе `.env.example`:

```env
APP_NAME=Advertisements API
DEBUG=1

POSTGRES_DB=ads_db
POSTGRES_USER=ads_user
POSTGRES_PASSWORD=ads_pass

DATABASE_URL=postgresql+asyncpg://ads_user:ads_pass@postgres:5432/ads_db

# Опционально (только если используете bootstrap root)
# BOOTSTRAP_ROOT_USERNAME=root
# BOOTSTRAP_ROOT_PASSWORD=some_short_password
```

### 6.2 `.env.test.example` (TEST)
Создайте `.env.test` на основе `.env.test.example`:

```env
APP_NAME=Advertisements API (tests)
DEBUG=0

DATABASE_URL=postgresql+asyncpg://ads_user:ads_pass@postgres_test:5432/ads_test_db
```

> Важно: в тестах `DATABASE_URL` должен указывать на `postgres_test` (имя сервиса в docker-compose).

---

## 7) Запуск проекта в Docker (DEV профиль)

### 7.1 Сборка и запуск
```bash
docker compose --profile dev up --build
```

Что происходит:
- запускается PostgreSQL (`postgres`)
- выполняются миграции `alembic upgrade head`
- поднимается API на `http://localhost:8000`

### 7.2 Swagger UI
- `http://localhost:8000/docs`

Остановка:
```bash
docker compose --profile dev down
```

---

## 8) Миграции Alembic

Миграции выполняются автоматически при старте контейнера `api` (dev) и перед тестами (test).

Ручной запуск миграций внутри контейнера:
```bash
docker compose --profile dev exec api alembic upgrade head
```

---

## 9) Эндпоинты API

### 9.1 Аутентификация
- `POST /login` — получить JWT (48h)

### 9.2 Пользователи
- `POST /user` — создать пользователя
- `GET /user/{user_id}` — получить пользователя
- `PATCH /user/{user_id}` — обновить пользователя (user: только себя; admin: любого)
- `DELETE /user/{user_id}` — удалить пользователя (user: только себя; admin: любого)

> Если прав нет — 403.

### 9.3 Объявления
- `POST /advertisement` — создать (только авторизованный)
- `GET /advertisement/{id}` — получить (публично)
- `PATCH /advertisement/{id}` — обновить (владелец или admin)
- `DELETE /advertisement/{id}` — удалить (владелец или admin)
- `GET /advertisement?...` — поиск/фильтры (публично)

#### Поиск и фильтрация `/advertisement`
Query‑параметры:
- `q` — общий поиск по `title/description/author`
- `title`, `description`, `author`
- `price_from`, `price_to`
- `created_from`, `created_to` (ISO)
- `limit` (1..200), `offset` (>=0)

---

## 10) HTTP-запросы для проверки (test_requests.http)

В корне проекта есть файл `test_requests.http` — удобно запускать из **PyCharm / IntelliJ / VS Code (REST Client)**.

Он включает сценарии:
- логин
- создание пользователей (user/admin)
- CRUD объявлений с проверкой прав
- поиск
- удаления

---

## 11) Тесты

Тесты находятся в `tests/`:
- `test_crud.py` — CRUD сценарий + права
- `test_search.py` — фильтры поиска
- `conftest.py` — фикстуры: создание уникальных пользователей + авторизованные клиенты

Технически тесты запускают приложение **внутри процесса** через `httpx.ASGITransport`, то есть **без поднятия отдельного uvicorn**.

---

## 12) Запуск тестов в Docker (TEST профиль)

```bash
docker compose --profile test up --build --abort-on-container-exit --exit-code-from tests
```

Ожидаемый результат:
- `5 passed`
- контейнер `tests` завершается с кодом `0`

---

## 13) pytest.ini и предупреждения

Если вы видите предупреждение:

- `DeprecationWarning: 'crypt' is deprecated ...`

Это предупреждение приходит **из зависимостей** (например, passlib), а не из вашего кода.  
Фильтр в `pytest.ini` позволяет не “засорять” вывод тестов нерелевантным предупреждением:

```ini
[pytest]
filterwarnings =
    ignore:'crypt' is deprecated and slated for removal in Python 3.13:DeprecationWarning
```

---

## 14) Требования по заданию — чек-лист

✅ `POST /login` → token, 48h, неверные креды → 401  
✅ CRUD пользователей: `GET/POST/PATCH/DELETE /user...`  
✅ Группы: `user`, `admin` (admin может всё)  
✅ Права неавторизованного пользователя: `POST /user`, `GET /user/{id}`, `GET /advertisement/{id}`, `GET /advertisement`  
✅ Права user: self PATCH/DELETE, свои объявления PATCH/DELETE, создание объявлений  
✅ 403 при недостатке прав  
✅ Docker + Alembic + PostgreSQL + автотесты  

---

## 15) Команды для проверки

### Запуск API (DEV)
```bash
docker compose --profile dev up --build
```

### Запуск тестов (TEST)
```bash
docker compose --profile test up --build --abort-on-container-exit --exit-code-from tests
```
