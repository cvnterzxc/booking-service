# Booking Service

Онлайн-запись к мастерам (барбершопы, салоны, репетиторы) вместо переписки в WhatsApp.

**Стек:** Python, FastAPI, SQLAlchemy 2, PostgreSQL, Alembic, Docker.

## Запуск локально

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env

docker compose up -d          # PostgreSQL на localhost:5432
alembic upgrade head          # создать таблицы
uvicorn app.main:app --reload # API на http://localhost:8000/docs
```

## Схема данных

- `users`: клиенты, мастера, админы (поле `role`)
- `masters`: профиль мастера, публичный `slug`, часовой пояс
- `services`: услуги мастера с длительностью и ценой (в тенге, целым числом)
- `working_hours`: рабочие интервалы по дням недели
- `bookings`: записи. Двойное бронирование запрещено на уровне PostgreSQL
  через `EXCLUDE USING gist` по `(master_id, tstzrange(starts_at, ends_at))`
