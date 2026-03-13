# CLAUDE.md — ITfresh Project Guide

Этот файл содержит всю необходимую информацию для работы с проектами ITfresh.
Читай его ПЕРЕД тем как начинать любую задачу.

---

## Сервер (brain-server)

| Параметр | Значение |
|----------|----------|
| IP | 212.69.85.169 |
| SSH root | `ssh root@212.69.85.169` |
| SSH user | `ssh itfresh@212.69.85.169` |
| Пароль (оба) | `Itfresh2012!!!` |
| SSH ключ | `~/.ssh/brain_vps` |
| ОС | Debian |

Подключение:
```bash
ssh -i ~/.ssh/brain_vps root@212.69.85.169
# или без ключа:
ssh root@212.69.85.169
# пароль: Itfresh2012!!!
```

---

## Проект AdminDB (CRM для IT-аутсорсинга)

### Доступ

| | |
|-|-|
| URL | https://adminbd.itfresh.ru |
| Домен | adminbd.itfresh.ru |
| Admin логин | `admin` |
| Admin пароль | `O-t9nW-FVhxxW-LCGqJByg` |

### Расположение на сервере

```
/opt/admindb/
  backend/          — FastAPI приложение (Python)
  frontend/dist/    — скомпилированный фронтенд (production)
  frontend-src/     — ИСХОДНИКИ фронтенда (React + Vite + TypeScript)
  frontend-src/src/ — .tsx компоненты, редактировать здесь
  deploy/           — docker-compose.yml, nginx, .env
/opt/backups/       — ежедневные бэкапы БД
```

### База данных PostgreSQL

| Параметр | Значение |
|----------|----------|
| Пользователь | `admindb` |
| Пароль | `II0Kc904aU2sarCYQ9D-p184oTzyE0gZ` |
| База | `admindb` |
| SECRET_KEY | `928d5f2bb091a24f26c626bda9b461750ff19a71ec2f822e4e699f46c1da0cc8` |
| FERNET_KEY | `jr9DR0Pjmn27VPJvKD5NRkPbDGMYPOsifQkXWbc3RH8=` |

### Стек технологий

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL + Alembic
- **Frontend:** React 18 + Vite + TypeScript + TailwindCSS
- **Инфраструктура:** Docker Compose + Nginx + Let's Encrypt (certbot)
- **Пользователи:** роли superadmin / admin / user, группы Руководство / Сотрудники

### Структура бэкенда

```
/opt/admindb/backend/app/
  models/       — client.py, user.py, tickets.py, field_options.py, ...
  schemas/      — Pydantic схемы
  api/v1/endpoints/ — clients.py, users.py, tickets.py, ...
  core/         — security, config
```

### Структура фронтенда (исходники)

```
/opt/admindb/frontend-src/src/
  pages/        — ClientsPage.tsx, TicketsPage.tsx, UsersPage.tsx, ...
  components/   — Sidebar.tsx, ClientDetail.tsx, ClientForm.tsx, ...
  api/          — clients.ts (все API вызовы)
  store/        — authStore.ts (Zustand)
  hooks/        — useDebounce.ts
  types.ts      — все TypeScript типы
  App.tsx       — роутинг
```

### Команды управления

```bash
# Статус контейнеров
ssh root@212.69.85.169 "cd /opt/admindb/deploy && docker compose ps"

# Логи бэкенда
ssh root@212.69.85.169 "cd /opt/admindb/deploy && docker compose logs backend --tail=50"

# Рестарт бэкенда
ssh root@212.69.85.169 "cd /opt/admindb/deploy && docker compose restart backend"

# Рестарт nginx
ssh root@212.69.85.169 "cd /opt/admindb/deploy && docker compose restart nginx"
```

### Сборка и деплой фронтенда

После изменения .tsx файлов в `/opt/admindb/frontend-src/src/`:

```bash
# 1. Собрать
ssh root@212.69.85.169 "docker run --rm -v /opt/admindb/frontend-src:/app -w /app node:20-alpine sh -c 'npm run build 2>&1'"

# 2. Задеплоить
ssh root@212.69.85.169 "cp -r /opt/admindb/frontend-src/dist/. /opt/admindb/frontend/dist/ && cd /opt/admindb/deploy && docker compose restart nginx"

# 3. Проверить
ssh root@212.69.85.169 "curl -s -o /dev/null -w '%{http_code}' https://adminbd.itfresh.ru"
# Должно вернуть 200
```

### Деплой изменений бэкенда

```bash
# Скопировать файлы на сервер
scp -i ~/.ssh/brain_vps local_file.py root@212.69.85.169:/opt/admindb/backend/app/...

# Пересобрать и рестартовать
ssh root@212.69.85.169 "cd /opt/admindb/deploy && docker compose up -d --build backend"
```

---

## Проект Agent Second Brain (Telegram бот)

### Что делает

Telegram бот для голосовых заметок. Расшифровывает голос → классифицирует → создаёт задачи в Todoist → сохраняет в Obsidian vault → ежедневный отчёт.

### Расположение

```
/home/itfresh/agent-second-brain/  — на сервере (запущен)
Brain/                              — в этом репо (документация и vault)
src/                               — исходный код бота
```

### Управление ботом

```bash
# Статус
ssh itfresh@212.69.85.169 "sudo systemctl status d-brain-bot"

# Логи
ssh itfresh@212.69.85.169 "sudo journalctl -u d-brain-bot -n 50"

# Рестарт
ssh itfresh@212.69.85.169 "sudo systemctl restart d-brain-bot"
```

---

## GitHub репозиторий

| Параметр | Значение |
|----------|----------|
| Репо | https://github.com/itfresh2025/Brain |
| SSH ключ на сервере | `~/.ssh/github_brain` |
| Локальный клон на сервере | `/home/itfresh/agent-second-brain/` |

### Правило: ВСЕГДА пушить изменения в GitHub

После любых изменений по любому проекту — коммит и пуш:

```bash
# С сервера
GIT_SSH_COMMAND='ssh -i ~/.ssh/github_brain' git -C /home/itfresh/agent-second-brain add -A
GIT_SSH_COMMAND='ssh -i ~/.ssh/github_brain' git -C /home/itfresh/agent-second-brain commit -m "описание изменений"
GIT_SSH_COMMAND='ssh -i ~/.ssh/github_brain' git -C /home/itfresh/agent-second-brain push
```

### Структура репо на GitHub

```
admindb/
  backend/    — исходники FastAPI
  frontend/   — dist + исходники
  deploy/     — docker-compose, nginx, конфиги
Brain/
  docs/       — документация
  vault/      — Obsidian заметки
  admindb/    — конфиги и пароли
```

---

## Workflow: как вносить изменения

### Изменение фронтенда (UI)

1. Редактировать файлы в `/opt/admindb/frontend-src/src/` на сервере (через SSH)
2. Или редактировать в репо `admindb/frontend/src/` и загрузить через scp
3. Собрать: `docker run ... node:20-alpine npm run build`
4. Задеплоить: `cp dist → frontend/dist && docker compose restart nginx`
5. Запушить в GitHub

### Изменение бэкенда (API)

1. Редактировать в `admindb/backend/app/`
2. Скопировать на сервер через scp
3. `docker compose up -d --build backend`
4. Запушить в GitHub

### Изменение моделей БД

1. Изменить модель в `models/`
2. Создать Alembic миграцию на сервере
3. Применить миграцию
4. Задеплоить бэкенд

---

## Полезные проверки

```bash
# Сайт работает?
curl -s -o /dev/null -w '%{http_code}' https://adminbd.itfresh.ru

# DNS смотрит на правильный сервер?
nslookup adminbd.itfresh.ru
# Должен вернуть 212.69.85.169

# Все контейнеры запущены?
ssh root@212.69.85.169 "cd /opt/admindb/deploy && docker compose ps"

# Здоровье API
curl -s https://adminbd.itfresh.ru/api/v1/health
```
