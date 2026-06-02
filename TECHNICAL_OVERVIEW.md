# 📊 Технический обзор проекта Web Shower Copy

## Оглавление
1. [Обзор архитектуры](#обзор-архитектуры)
2. [Структура проекта](#структура-проекта)
3. [Компоненты и технологии](#компоненты-и-технологии)
4. [Поток данных и взаимодействие](#поток-данных-и-взаимодействие)
5. [Развёртывание и CI/CD](#развёртывание-и-cicd)

---

## Обзор архитектуры

Проект реализован как **микросервисная архитектура** с использованием Docker Compose:

```
┌─────────────────────────────────────────────────────────────┐
│                      Пользователь                            │
│                   (Web браузер)                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                    http://localhost:80
                         │
         ┌───────────────▼────────────────┐
         │         Nginx (Gateway)         │
         │  маршрутизация + CORS           │
         └─┬──────────┬──────────┬────────┬┘
           │          │          │        │
      /auth/      /booking/  /comments/  /feedback/
           │          │          │        │
    ┌──────▼─┐  ┌──────▼─┐  ┌───▼────┐  ┌───▼─────┐
    │  Auth   │  │ Booking│  │Comments│  │ Feedback│
    │ Service │  │Service │  │Service │  │ Service │
    └──────┬─┘  └──────┬─┘  └───┬────┘  └───┬─────┘
           │          │          │        │
           └──────────┴──────────┴────────┘
                      │
             ┌────────▼─────────┐
             │  PostgreSQL DB   │
             │ (4 отдельных БД) │
             └──────────────────┘
```

**Ключевые характеристики:**
* 4 независимых Django-приложения (микросервисы)
* Каждый микросервис имеет собственную базу данных
* Nginx работает как API gateway и обратный прокси
* Docker Compose управляет оркестрацией контейнеров
* PostgreSQL хранит данные всех сервисов

---

## Структура проекта

### Корневая папка: `/home/nastya/src/web_shower_copy`

```
web_shower_copy/
├── auth-service/           # Сервис авторизации и регистрации
├── booking-service/        # Сервис бронирования душевых
├── comments-service/       # Сервис комментариев с SSE
├── feedback-service/       # Сервис обратной связи (VK API)
├── nginx/                  # Конфигурация API gateway
├── postgres-init/          # Инициализация баз данных
├── .github/                # GitHub Actions CI/CD
├── assets/                 # Статические ресурсы (видео и прочее)
├── docker-compose.yml      # Оркестрация контейнеров
├── .env                    # Переменные окружения (не коммитится)
├── .env.example            # Шаблон переменных окружения
└── README.md               # Документация проекта
```

---

## Компоненты и технологии

### 1️⃣ **Auth-Service** (Сервис авторизации)

**Расположение:** `auth-service/`

**Назначение:**
* Регистрация новых пользователей
* Вход (аутентификация) пользователя
* Генерация и валидация JWT-токенов
* Проверка данных пользователя

**Структура:**
```
auth-service/
├── app/
│   ├── models.py          # (пусто) — используется встроенная User модель Django
│   ├── views.py           # API endpoints для регистрации и входа
│   ├── urls.py            # Маршруты: /auth/register/, /auth/login/, /auth/me/
│   ├── jwt_utils.py       # Функции генерации и валидации JWT
│   ├── templates/
│   │   └── app/login.html # Страница входа (HTML форма)
│   └── migrations/        # Миграции БД
├── config/
│   ├── settings.py        # Django конфигурация
│   ├── urls.py            # Главный URL router
│   └── wsgi.py            # WSGI приложение для Gunicorn
├── static/css/styles.css  # CSS стили для login.html
├── Dockerfile             # Контейнер конфигурация
├── requirements.txt       # Python зависимости (Django, psycopg2, PyJWT...)
└── entrypoint.sh          # Скрипт запуска: миграции + Gunicorn
```

**Технологии:**
* **Django ORM** — работа с пользователями через встроенную модель `User`
* **PyJWT** — создание и декодирование JWT токенов
* **PostgreSQL** — хранение пользователей в БД `auth_db`
* **Gunicorn** — WSGI-сервер (2 worker'а с gthread)

**API endpoints:**
```
POST   /auth/register/     # Регистрация пользователя
POST   /auth/login/        # Вход пользователя
GET    /auth/login-page/   # HTML страница входа
POST   /auth/token/refresh/ # Обновление токена
GET    /auth/me/           # Получить текущего пользователя
```

**Поток данных — Регистрация:**
```
Браузер (form)
    ↓ POST /auth/register/ (name, email, password)
    ↓ Nginx proxy_pass к auth-service:8000
    ↓ auth/views.py::register()
    ├─ Валидация: имя (русские буквы), email (уникальность), пароль (6+ символов)
    ├─ Создание User в PostgreSQL (auth_db)
    ├─ Генерация JWT токенов (access + refresh)
    ↓ Возврат JSON {access, refresh, user}
    ↓ Браузер сохраняет токены в localStorage
```

**JWT токены:**
* **Access token** — короткий (24 часа), используется в Authorization header
* **Refresh token** — длительный (7 дней), для получения нового access token'а
* **Payload:** `{user_id, email, username}`

---

### 2️⃣ **Booking-Service** (Сервис бронирования)

**Расположение:** `booking-service/`

**Назначение:**
* Получение доступных слотов (времени) для бронирования
* Создание бронирования (запись в душевую)
* Просмотр личных бронирований
* Отмена бронирования

**Структура:**
```
booking-service/
├── app/
│   ├── models.py          # Модель Booking (дата, время, пользователь)
│   ├── views.py           # API endpoints для слотов и бронирования
│   ├── urls.py            # Маршруты: /booking/, /booking/slots/, /booking/my/
│   ├── jwt_utils.py       # Парсинг JWT из Authorization header
│   ├── templates/
│   │   └── app/booking.html # Главная страница с интерфейсом бронирования
│   └── migrations/        # Миграции БД
├── config/
│   ├── settings.py        # Django конфигурация
│   ├── urls.py            
│   └── wsgi.py            
├── static/css/styles.css  # CSS стили для интерфейса
├── Dockerfile             
├── requirements.txt       # Django, psycopg2, PyJWT...
└── entrypoint.sh          # Запуск с миграциями и Gunicorn
```

**Модель данных — Booking:**
```python
class Booking(models.Model):
    user_id = models.IntegerField()           # ID пользователя из JWT
    username = models.CharField(max_length=150) # Имя пользователя
    date = models.DateField()                 # Дата: YYYY-MM-DD
    time = models.TimeField()                 # Время: HH:MM
    created_at = models.DateTimeField()       # Время создания

    unique_together = [("date", "time")]      # Один слот = одна бронь!
```

**Технологии:**
* **Django ORM** — работа с моделью Booking
* **PostgreSQL** — хранение данных в БД `booking_db`
* **JWT парсинг** — из Authorization header (без FK на auth-service)
* **Gunicorn** — 2 worker'а

**API endpoints:**
```
GET    /booking/           # HTML страница
GET    /booking/slots/?date=YYYY-MM-DD  # Список всех слотов за дату
GET    /booking/my/        # Мои бронирования (требует JWT)
POST   /booking/create/    # Создать бронирование (JSON: {date, time})
DELETE /booking/cancel/<id>/ # Отменить бронирование
```

**Доступные слоты:**
* **Время:** 08:00 - 21:30 (30-минутные интервалы)
* **Всего слотов в день:** 28 слотов
* **Статусы слота:**
  - `"free"` — свободен
  - `"taken"` — занят другим пользователем
  - `"mine"` — мое бронирование

**Поток данных — Бронирование:**
```
Браузер: выбирает дату и время
    ↓ GET /booking/slots/?date=2026-06-02
    ↓ Nginx → booking-service:8000
    ↓ booking/views.py::slots()
    ├─ Выбирает все Booking на эту дату из БД
    ├─ Парсит JWT из Authorization header
    ├─ Определяет статус каждого слота (free/taken/mine)
    ↓ Возврат JSON {date, slots: [...]}
    ↓ Браузер отображает доступные слоты

Браузер: нажимает "Забронировать"
    ↓ POST /booking/create/ (JSON: {date, time})
    ↓ require_auth декоратор проверяет JWT
    ↓ booking/views.py::create_booking()
    ├─ Валидирует дату, время и JWT
    ├─ Проверяет уникальность (date, time)
    ├─ Создает запись Booking в PostgreSQL
    ↓ Возврат JSON {success: true, booking: {...}}
```

---

### 3️⃣ **Comments-Service** (Сервис комментариев с SSE)

**Расположение:** `comments-service/`

**Назначение:**
* Хранение комментариев (отзывов) пользователей
* **Server-Sent Events (SSE)** — передача новых комментариев клиентам в реальном времени
* Отображение ленты комментариев

**Структура:**
```
comments-service/
├── app/
│   ├── models.py          # Модель Comment (автор, текст, дата)
│   ├── views.py           # API endpoints для комментариев + SSE
│   ├── urls.py            # /comments/, /comments/stream/
│   ├── jwt_utils.py       # JWT парсинг
│   ├── templates/
│   │   └── app/comments.html # Страница с SSE-клиентом (JavaScript)
│   └── migrations/        # Миграции БД
├── config/
│   ├── settings.py        
│   ├── urls.py            
│   └── wsgi.py            
├── static/css/styles.css  
├── Dockerfile             
├── requirements.txt       
└── entrypoint.sh          # Gunicorn с worker-class gthread для SSE
```

**Модель данных — Comment:**
```python
class Comment(models.Model):
    user_id = models.IntegerField()           # ID пользователя из JWT
    author = models.CharField(max_length=150) # Имя автора
    text = models.TextField(max_length=1000)  # Текст комментария
    created_at = models.DateTimeField()       # Время создания

    class Meta:
        ordering = ["-created_at"]            # Новые комментарии первыми
```

**Технологии:**
* **Server-Sent Events (SSE)** — HTTP streaming для real-time уведомлений
* **Django ORM** — работа с Comment
* **PostgreSQL** — хранение в БД `comments_db`
* **Gunicorn gthread** — многопоточный worker для долгоживущих SSE соединений
* **JavaScript EventSource API** — клиент для слушания SSE

**API endpoints:**
```
GET    /comments/          # HTML страница с комментариями
POST   /comments/          # Создать комментарий (JSON: {text})
GET    /comments/stream/   # SSE stream — слушаем новые комментарии
```

**Конфигурация Nginx для SSE:**
```nginx
location /comments/stream/ {
    proxy_buffering       off;      # Отключаем буферизацию
    proxy_cache           off;      # Отключаем кэш
    proxy_read_timeout    360s;     # 6 минут на сессию SSE
    proxy_http_version    1.1;
    proxy_set_header Connection "";
    chunked_transfer_encoding on;   # Chunked transfer для streaming
}
```

**Поток данных — SSE Streaming:**
```
Браузер загружает /comments/
    ↓ JavaScript код запускает новый EventSource('/comments/stream/')
    ↓ Браузер отправляет GET запрос с Connection: keep-alive
    ↓ Nginx отключает буферизацию и проксирует к comments-service:8000
    ↓ comments/views.py::stream() — Django generator
    ├─ Отправляет история комментариев
    ├─ Затем входит в цикл ожидания новых комментариев
    ├─ Когда создается новый Comment в БД, сервер отправляет:
    │   data: {"id": 123, "author": "Ivan", "text": "Good!"}
    ├─ Браузер получает событие, JavaScript обновляет DOM
    └─ Соединение остается открытым, ждет следующих комментариев

Другой браузер добавляет комментарий
    ↓ POST /comments/ (JSON: {text})
    ↓ comments/views.py::add_comment()
    ├─ Сохраняет Comment в PostgreSQL
    ├─ Все активные SSE соединения получают событие
    ↓ Лента обновляется на всех клиентах одновременно!
```

**Особенность SSE:**
* Однонаправленный канал (сервер → клиент)
* Автоматическое переподключение при потере связи
* Идеально для real-time обновлений (лента, уведомления)
* Проще WebSocket, работает через обычный HTTP

---

### 4️⃣ **Feedback-Service** (Сервис обратной связи)

**Расположение:** `feedback-service/`

**Назначение:**
* Сохранение сообщений обратной связи (forms feedback)
* Отправка уведомлений администратору через **VK API** в личные сообщения
* Хранение истории всех отзывов

**Структура:**
```
feedback-service/
├── app/
│   ├── models.py          # Модель FeedbackMessage
│   ├── views.py           # API endpoints + отправка в VK API
│   ├── urls.py            # /feedback/, /feedback/submit/
│   ├── templates/
│   │   └── app/feedback.html # Форма обратной связи
│   └── migrations/        # Миграции БД
├── config/
│   ├── settings.py        # VK_GROUP_TOKEN, VK_ADMIN_ID, EMAIL_*
│   ├── urls.py            
│   └── wsgi.py            
├── static/css/styles.css  
├── Dockerfile             
├── requirements.txt       # Django, requests, psycopg2...
└── entrypoint.sh          # Запуск с Gunicorn
```

**Модель данных — FeedbackMessage:**
```python
class FeedbackMessage(models.Model):
    SUBJECT_CHOICES = [
        ("booking", "Бронирование"),
        ("technical", "Техническая проблема"),
        ("suggestion", "Предложение"),
        ("other", "Другое"),
    ]
    
    name = models.CharField(max_length=100)      # Имя отправителя
    email = models.EmailField()                  # Email отправителя
    subject = models.CharField(choices=SUBJECT_CHOICES)  # Тема
    message = models.TextField()                 # Текст сообщения
    created_at = models.DateTimeField(auto_now_add=True)
```

**Технологии:**
* **Python requests** — HTTP-клиент для VK API
* **VK API method `messages.send`** — отправка личных сообщений администратору
* **PostgreSQL** — хранение в БД `feedback_db`
* **Django ORM**
* **Gunicorn** — 2 worker'а

**VK API интеграция:**
```python
# feedback/views.py::submit_feedback()
if settings.VK_GROUP_TOKEN and settings.VK_ADMIN_ID:
    vk_message = f"""💬 Обратная связь
    👤 Имя: {name}
    📧 Email: {email}
    📌 Тема: {subject_label}
    💭 Сообщение: {message}
    🕐 {current_time}
    """
    
    resp = http_requests.get(
        "https://api.vk.com/method/messages.send",
        params={
            "user_id": settings.VK_ADMIN_ID,      # ID админа
            "message": vk_message,
            "random_id": random.randint(0, 2**31), # Уникальный ID для дедупликации
            "access_token": settings.VK_GROUP_TOKEN,
            "v": "5.131",                         # VK API версия
        },
        timeout=5,
    )
```

**API endpoints:**
```
GET    /feedback/          # HTML страница с формой
POST   /feedback/submit/   # Отправить отзыв (JSON)
```

**Переменные окружения для VK:**
```
VK_GROUP_TOKEN=vk1.a.sAbBiBYVnIMcYuH...  # Токен группы (права на messages.send)
VK_GROUP_ID=239291724                     # ID группы ВКонтакте
VK_ADMIN_ID=341254622                     # ID администратора (пользователя)
```

**Поток данных — Отправка feedback в VK:**
```
Пользователь заполняет форму обратной связи
    ↓ POST /feedback/submit/ (JSON: {name, email, subject, message})
    ↓ Nginx → feedback-service:8000
    ↓ feedback/views.py::submit_feedback()
    ├─ Валидирует все поля
    ├─ Сохраняет FeedbackMessage в PostgreSQL (feedback_db)
    ├─ Формирует красивое сообщение с эмодзи
    ├─ Отправляет GET запрос к VK API:
    │   GET https://api.vk.com/method/messages.send?
    │       user_id=341254622&
    │       message=💬 Обратная связь...&
    │       random_id=123456789&
    │       access_token=vk1.a.sAbBiBYVnIMcYuH...&
    │       v=5.131
    ├─ VK API возвращает ответ (message_id или ошибка)
    ├─ Логирует результат отправки
    ↓ Браузер получает {success: true}
    
Администратор видит сообщение в личных сообщениях ВКонтакте!
```

---

### 5️⃣ **Nginx** (API Gateway и обратный прокси)

**Расположение:** `nginx/`

**Назначение:**
* Точка входа для всех HTTP запросов (порт 80)
* Маршрутизация запросов на соответствующие микросервисы
* Управление CORS заголовками
* Буферизация и кэширование
* SSL/TLS (в production)

**Структура:**
```
nginx/
├── Dockerfile              # FROM nginx:alpine
├── nginx.conf             # Главная конфигурация
└── (default nginx logs и кэш)
```

**nginx.conf — Upstream определения:**
```nginx
upstream auth      { server auth-service:8000; }
upstream booking   { server booking-service:8000; }
upstream comments  { server comments-service:8000; }
upstream feedback  { server feedback-service:8000; }

server {
    listen 80;
    client_max_body_size 10M;
}
```

**Маршрутизация запросов:**
```nginx
location = /              { return 302 /auth/; }
location /auth/           { proxy_pass http://auth; ... }
location /booking/        { proxy_pass http://booking; ... }
location /comments/stream/ { proxy_pass http://comments; proxy_buffering off; ... }
location /comments/       { proxy_pass http://comments; ... }
location /feedback/       { proxy_pass http://feedback; ... }
```

**CORS конфигурация:**
```nginx
add_header Access-Control-Allow-Origin "*" always;
add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
```

**Proxy headers:**
```nginx
proxy_set_header Host              $host;
proxy_set_header X-Real-IP         $remote_addr;
proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header Authorization     $http_authorization;
```

**HTTP-запрос пользователя:**
```
Браузер: GET http://localhost/booking/slots/?date=2026-06-02

  ↓ DNS resolves localhost → 127.0.0.1
  ↓ TCP соединение к порту 80
  ↓ HTTP запрос идёт к Nginx контейнеру

Nginx получает запрос:
  ↓ Читает конфиг (nginx.conf)
  ↓ Проверяет location = /booking/
  ↓ Выполняет proxy_pass http://booking (= http://booking-service:8000)
  ↓ Docker DNS преобразует booking-service в IP контейнера
  ↓ Форвардит запрос с proxy headers

booking-service:8000 получает запрос:
  ├─ Видит proxy headers (X-Real-IP, Authorization)
  ├─ Обрабатывает запрос (Django views)
  ├─ Возвращает JSON ответ

Nginx получает ответ:
  ├─ Добавляет CORS заголовки
  ↓ Отправляет браузеру

Браузер получает ответ с CORS и может обработать JSON
```

---

### 6️⃣ **PostgreSQL** (Единая база данных)

**Расположение:** `postgres-init/init.sql`

**Назначение:**
* Централизованное хранилище всех данных
* Каждый микросервис имеет свою БД (разделение данных)
* Shared database = общая инфраструктура, но изолированные схемы

**Инициализация БД:**
```sql
CREATE DATABASE auth_db;        -- Пользователи (User)
CREATE DATABASE booking_db;     -- Бронирования (Booking)
CREATE DATABASE comments_db;    -- Комментарии (Comment)
CREATE DATABASE feedback_db;    -- Отзывы (FeedbackMessage)
```

**Базы данных:**

| БД | Таблицы | Сервис | Описание |
|---|---|---|---|
| `auth_db` | `auth_user` | auth-service | Пользователи системы |
| `booking_db` | `app_booking` | booking-service | Бронирования слотов |
| `comments_db` | `app_comment` | comments-service | Комментарии/отзывы |
| `feedback_db` | `app_feedbackmessage` | feedback-service | Сообщения обратной связи |

**Технологии:**
* **PostgreSQL 16 Alpine** — легкий образ на основе Alpine Linux
* **django.db.backends.postgresql** — Django ORM драйвер
* **psycopg2-binary** — Python адаптер для PostgreSQL
* **Healthcheck** — Nginx ждет `pg_isready` перед стартом сервисов

**Docker Compose конфиг:**
```yaml
postgres:
  image: postgres:16-alpine
  environment:
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  volumes:
    - pg_data:/var/lib/postgresql/data
    - ./postgres-init:/docker-entrypoint-initdb.d
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
```

---

### 7️⃣ **Docker Compose** (Оркестрация)

**Файл:** `docker-compose.yml`

**Назначение:**
* Определение всех сервисов (контейнеров)
* Конфигурация сетей и томов
* Управление зависимостями между сервисами
* One-command deployment

**Сервисы:**
1. `postgres` — БД (публикует порт 5432 в сети)
2. `auth-service` — Django приложение (порт 8000, не публикуется)
3. `booking-service` — Django приложение (порт 8000, не публикуется)
4. `comments-service` — Django приложение (порт 8000, не публикуется)
5. `feedback-service` — Django приложение (порт 8000, не публикуется)
6. `nginx` — API gateway (публикует порт 80 на хост)

**Внутренняя сеть Docker:**
```
web_shower_copy_default (user-defined bridge network)

Все контейнеры подключены к этой сети
Разрешено общение по имени сервиса (DNS):
  auth-service:8000
  booking-service:8000
  comments-service:8000
  feedback-service:8000
  postgres:5432
```

**Том данных:**
```yaml
volumes:
  pg_data: {}  # Именованный том для /var/lib/postgresql/data
              # Сохраняет данные БД между перезапусками контейнеров
```

**Команды управления:**
```bash
docker compose up --build        # Сборка образов и запуск
docker compose down              # Остановка и удаление контейнеров
docker compose down -v           # Остановка и очистка томов (ОПАСНО!)
docker compose logs -f service   # Просмотр логов
docker compose ps                # Статус контейнеров
docker compose exec service cmd  # Выполнить команду в контейнере
```

---

## Поток данных и взаимодействие

### Сценарий 1: Регистрация и вход

```
User в браузере:
┌─────────────────────────────┐
│  Открывает http://localhost │
└──────────────┬──────────────┘
               ↓
          Nginx на :80
               ↓
    redirect → /auth/login-page/
               ↓
        auth-service:8000
               ↓
    Возвращает login.html
               ↓
   Браузер отображает форму
        (HTML + CSS + JS)

User заполняет: email, password, name
       ↓
   JavaScript отправляет:
   POST /auth/register/
   {name, email, password}
       ↓
    Nginx (маршрутизация)
       ↓
 auth-service:8000 (views.py)
       ↓
   Валидация данных
   (сложность пароля, уникальность email)
       ↓
   Django ORM создает User
   ↓
   PostgreSQL (auth_db)
   ↓
   Генерируется JWT токен:
   Header: {"alg": "HS256", "typ": "JWT"}
   Payload: {"user_id": 1, "email": "...", "exp": ...}
   Signature: HMAC-SHA256(header.payload, SECRET_KEY)
       ↓
   Возврат JSON:
   {
     "access": "eyJhbGciOiJIUzI1NiIs...",
     "refresh": "eyJhbGciOiJIUzI1NiIs...",
     "user": {id, name, email}
   }
       ↓
   JavaScript сохраняет в localStorage
   ↓
   User перенаправляется на /booking/
```

### Сценарий 2: Бронирование слота

```
User на /booking/ странице

1️⃣ Получить список слотов:

   User выбирает дату в календаре
   JavaScript отправляет:
   GET /booking/slots/?date=2026-06-02
   Header: Authorization: Bearer eyJhbGciOi...
       ↓
    Nginx маршрутизирует
       ↓
booking-service:8000::slots()
       ↓
   Парсит JWT из Authorization header
   Extract: user_id = 1
       ↓
   Query: SELECT time, user_id FROM app_booking
          WHERE date = '2026-06-02'
       ↓
   PostgreSQL (booking_db) возвращает:
   [(10:00, 2), (10:30, 1), (11:00, None), ...]
       ↓
   Django преобразует в JSON:
   {
     "date": "2026-06-02",
     "slots": [
       {"time": "08:00", "status": "free"},
       {"time": "08:30", "status": "taken"},
       {"time": "09:00", "status": "mine"},
       ...
     ]
   }
       ↓
   Браузер получает JSON
   JavaScript отображает слоты с цветами:
   🟢 free (зеленый, clickable)
   🔴 taken (красный, disabled)
   🔵 mine (синий, your booking)

2️⃣ Забронировать слот:

   User нажимает на свободный слот (08:00)
   JavaScript отправляет:
   POST /booking/create/
   {date: "2026-06-02", time: "08:00"}
   Header: Authorization: Bearer ...
       ↓
    Nginx маршрутизирует
       ↓
booking-service:8000::create_booking()
       ↓
   @require_auth декоратор:
   ├─ Парсит JWT
   ├─ Проверяет подпись (SECRET_KEY)
   ├─ Проверяет expiration
   ├─ Extract: user_id = 1, username = "Ivan"
       ↓
   Валидирует date и time
       ↓
   Проверяет UNIQUE constraint:
   SELECT * FROM app_booking
   WHERE date = '2026-06-02' AND time = '08:00'
   (должна быть пуста)
       ↓
   Создает запись:
   INSERT INTO app_booking
   (user_id, username, date, time, created_at)
   VALUES (1, 'Ivan', '2026-06-02', '08:00:00', NOW())
       ↓
   PostgreSQL возвращает ID новой записи
       ↓
   Django возвращает JSON:
   {
     "success": true,
     "booking": {
       "id": 42,
       "user_id": 1,
       "username": "Ivan",
       "date": "2026-06-02",
       "time": "08:00",
       "created_at": "02.06.2026 15:30"
     }
   }
       ↓
   Браузер отображает
   "✅ Вы забронировали слот на 08:00"
```

### Сценарий 3: SSE Streaming (комментарии)

```
User открывает /comments/

1️⃣ Инициализация SSE:

   HTML загружает comments.html
   JavaScript код:
   const source = new EventSource('/comments/stream/');
       ↓
   Браузер отправляет:
   GET /comments/stream/
   Accept: text/event-stream
   (специальный заголовок для SSE)
       ↓
    Nginx маршрутизирует (с proxy_buffering off)
       ↓
comments-service:8000::stream()
       ↓
   Django generator function:
   def stream(request):
       yield f"data: {json.dumps(comment)}\n\n"  # История
       while True:  # Вечный loop
           новый_комментарий = слушаем БД
           yield f"data: {json.dumps(новый_комментарий)}\n\n"
       ↓
   Nginx отправляет response с headers:
   Content-Type: text/event-stream
   Cache-Control: no-cache
   Connection: keep-alive
       ↓
   Браузер получает первый chunk (история комментариев):
   data: {"id": 1, "author": "Alice", "text": "Хороший сервис!"}
   data: {"id": 2, "author": "Bob", "text": "Согласен!"}
       ↓
   JavaScript парсит каждый data: блок
   Обновляет DOM (добавляет комментарии на страницу)
   ↓
   Браузер остается подключен к /comments/stream/
   (TCP соединение открыто, не закрывается!)

2️⃣ Другой user добавляет комментарий:

   User 2 заполняет форму "Добавить комментарий"
   Текст: "Отличная система!"
       ↓
   POST /comments/
   {text: "Отличная система!"}
   Authorization: Bearer ...
       ↓
    Nginx маршрутизирует
       ↓
comments-service:8000::add_comment()
       ↓
   Парсит JWT (user_id = 2, author = "Bob")
   Создает Comment:
   INSERT INTO app_comment
   (user_id, author, text, created_at)
   VALUES (2, 'Bob', 'Отличная система!', NOW())
       ↓
   PostgreSQL сохраняет, возвращает ID
       ↓
   Django возвращает успех браузеру User 2
       ↓
   Database push notification (или Django сигнал):
   Уведомляет генератор stream() о новом комментарии
       ↓
   stream() (в User 1 браузере!) выполняет:
   yield f"data: {json.dumps(new_comment)}\n\n"
       ↓
   Nginx отправляет chunk User 1 браузеру
       ↓
   EventSource в браузере User 1 срабатывает:
   source.onmessage = function(event) {
       const comment = JSON.parse(event.data);
       // Добавить на страницу
   }
       ↓
   User 1 видит новый комментарий Bob'а
   БЕЗ перезагрузки страницы! ✨ Real-time!
```

### Сценарий 4: Отправка фидбека в VK

```
User открывает /feedback/

   Видит форму:
   - Имя
   - Email
   - Тема (select: booking, technical, suggestion, other)
   - Сообщение (textarea)

   User заполняет форму:
   Имя: Иван Петров
   Email: ivan@gmail.com
   Тема: technical
   Сообщение: У меня не работает бронирование!
       ↓
   Нажимает "Отправить отзыв"
       ↓
   JavaScript отправляет:
   POST /feedback/submit/
   {
     name: "Иван Петров",
     email: "ivan@gmail.com",
     subject: "technical",
     message: "У меня не работает бронирование!"
   }
       ↓
    Nginx маршрутизирует
       ↓
feedback-service:8000::submit_feedback()
       ↓
   Валидирует все поля (не пусты, email формат)
       ↓
   Сохраняет в БД:
   INSERT INTO app_feedbackmessage
   (name, email, subject, message, created_at)
   VALUES ('Иван Петров', 'ivan@gmail.com', 'technical',
           'У меня не работает бронирование!', NOW())
       ↓
   PostgreSQL (feedback_db) сохраняет,
   возвращает ID
       ↓
   Django проверяет:
   if settings.VK_GROUP_TOKEN and settings.VK_ADMIN_ID:
       ↓
   Формирует красивое сообщение:
   vk_message = """
   💬 Обратная связь
   👤 Имя: Иван Петров
   📧 Email: ivan@gmail.com
   📌 Тема: Техническая проблема
   💭 Сообщение: У меня не работает бронирование!
   🕐 02.06.2026 15:45
   """
       ↓
   Генерирует random_id (для дедупликации):
   random_id = random.randint(0, 2**31)
       ↓
   Отправляет HTTP GET запрос к VK API:
   GET https://api.vk.com/method/messages.send?
       user_id=341254622&
       message=💬 Обратная связь...&
       random_id=123456789&
       access_token=vk1.a.sAbBiBYVnIMcYuH...&
       v=5.131
       ↓
   VK API обрабатывает запрос:
   ├─ Проверяет access_token
   ├─ Проверяет rights (messages.send)
   ├─ Дедуплицирует по random_id
   ├─ Отправляет message_id в личные сообщения
   │  пользователю с ID 341254622
   ├─ Возвращает JSON: {"response": 12345}
       ↓
   Django логирует результат:
   "VK message sent successfully: {'response': 12345}"
       ↓
   Возвращает браузеру:
   {success: true, message: "Спасибо за отзыв!"}
       ↓
   User видит:
   "✅ Ваш отзыв отправлен администратору"

👨‍💼 Администратор в ВКонтакте получает сообщение:
   💬 Обратная связь
   👤 Иван Петров
   📧 ivan@gmail.com
   📌 Техническая проблема
   💭 У меня не работает бронирование!
   🕐 02.06.2026 15:45
```

---

## Развёртывание и CI/CD

### Docker Compose — локальный запуск

**Команда:**
```bash
docker compose up --build
```

**Что происходит:**
1. Docker читает `docker-compose.yml`
2. Для каждого сервиса:
   - Создает Dockerfile → собирает образ
   - Запускает контейнер из образа
3. Создает user-defined network `web_shower_copy_default`
4. Запускает контейнер `postgres` с healthcheck
5. Ожидает пока PostgreSQL будет готов
6. Запускает 4 Django сервиса (зависит от postgres:healthy)
7. Запускает Nginx (зависит от всех сервисов)
8. Выполняет entrypoint.sh в каждом контейнере:
   - `python manage.py migrate --noinput` (применить миграции)
   - `gunicorn config.wsgi:application` (запустить WSGI сервер)

**Ports:**
- `localhost:80` → Nginx (публично видна)
- Остальные порты (5432, 8000) → только в Docker network

### GitHub Actions — CI/CD Pipeline

**Папка:** `.github/workflows/`

#### CI Pipeline (`.github/workflows/ci.yml`)

**Триггеры:**
- `push` в ветки: `main`, `dev`
- `pull_request` в ветку `main`

**Jobs:**

1️⃣ **lint-and-check** — статические проверки
```yaml
- Checkout код из git
- Setup Python 3.11
- pip install requirements.txt
- python manage.py check --deploy
- python manage.py migrate --check
```

2️⃣ **build-monolith** — сборка (если был на корне)
```yaml
- docker build -t shower-booking:SHA .
```

3️⃣ **build-microservices** — сборка микросервисов
```yaml
matrix:
  service: [auth-service, booking-service, ...]

для каждого:
  docker build -t shower-booking-SERVICE:SHA ./SERVICE
```

**Результат:** Docker образы готовы к использованию

#### CD Pipeline (`.github/workflows/cd.yml`)

**Триггер:**
- `push` только в ветку `main`

**Действия:**
1. Login в GitHub Container Registry (GHCR)
2. Build Docker images
3. Push images в `ghcr.io/owner/shower-booking-SERVICE:SHA`
4. Tag как `latest` если в main

**Registry URL:**
```
ghcr.io/nastya-sedreeva/shower-booking-auth-service:abc123
ghcr.io/nastya-sedreeva/shower-booking-booking-service:abc123
ghcr.io/nastya-sedreeva/shower-booking-comments-service:abc123
ghcr.io/nastya-sedreeva/shower-booking-feedback-service:abc123
```

**Использование в production:**
```yaml
image: ghcr.io/nastya-sedreeva/shower-booking-auth-service:latest
```

### Переменные окружения (`.env`)

```bash
# ===== Database =====
DB_ENGINE=django.db.backends.postgresql
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432
POSTGRES_PASSWORD=postgres

DB_NAME_AUTH=auth_db
DB_HOST_AUTH=postgres

DB_NAME_BOOKING=booking_db
DB_HOST_BOOKING=postgres

# ... и т.д. для каждой БД

# ===== JWT =====
JWT_SECRET_KEY=super-secret-key-change-in-production
JWT_EXPIRATION_HOURS=24

# ===== VK API =====
VK_GROUP_TOKEN=vk1.a.sAbBiBYVnIMcYuH...
VK_GROUP_ID=239291724
VK_ADMIN_ID=341254622

# ===== Email =====
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=app-password

# ===== Other =====
DEBUG=False  # True только для разработки!
SECRET_KEY=change-this-to-random-string
CORS_ALLOWED_ORIGINS=http://localhost:80,http://localhost:3000
```

---

## Заключение

### Ключевые моменты архитектуры:

✅ **Микросервисная архитектура**
- Каждый сервис = отдельный Django app
- Легко масштабировать отдельные компоненты
- Независимые базы данных

✅ **API Gateway (Nginx)**
- Единая точка входа
- Маршрутизация запросов
- CORS управление
- Load balancing потенциал

✅ **Real-time возможности (SSE)**
- Server-Sent Events для комментариев
- Двусторонняя коммуникация в браузере
- Без WebSocket (проще для разработки)

✅ **VK API интеграция**
- Отправка фидбека в личные сообщения
- random_id для дедупликации
- Асинхронная отправка (не блокирует ответ)

✅ **Docker контейнеризация**
- Воспроизводимость
- Легкое развертывание
- CI/CD автоматизация

✅ **JWT аутентификация**
- Stateless (не нужна сессионная БД)
- Передача данных в Authorization header
- Безопасная генерация и валидация

---

## Защита проекта — примерные вопросы и ответы

**Q: Почему микросервисы, а не монолит?**
A: Микросервисы позволяют:
- Независимо разрабатывать каждый компонент
- Масштабировать критичные сервисы отдельно
- Использовать разные БД для разных предметных областей
- Упростить тестирование и развертывание

**Q: Как контейнеры общаются между собой?**
A: Через Docker user-defined bridge network `web_shower_copy_default`. DNS разрешает имена сервисов в IP адреса контейнеров.

**Q: Что если Nginx упадет?**
A: `restart: unless-stopped` перезапустит контейнер. Но сам сервис будет недоступен ~ 5 сек.

**Q: Как работает SSE streaming?**
A: Django generator отправляет `data: json\n\n` чанки. Nginx отключает буферизацию. Браузер слушает EventSource и обновляет UI при получении событий.

**Q: Как безопасна отправка в VK API?**
A: Токен группы хранится в .env (не в git). random_id предотвращает дубликаты. API ключ имеет ограниченные права (только messages.send).

**Q: Почему JWT вместо сессионных cookies?**
A: JWT stateless → не нужно хранить сессии на сервере. Легче масштабировать. Подходит для микросервисов.

**Q: Что если создать две одинаковые бронирования одновременно?**
A: UNIQUE constraint (date, time) в БД гарантирует, что PostgreSQL отклонит второй INSERT. Один из клиентов получит ошибку.
