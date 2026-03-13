# Brain Project — Claude Code Guide

## Сервер (brain-server)

- **IP:** 212.69.85.169
- **SSH:** `ssh root@212.69.85.169` (пароль: `Itfresh2012!!!`)
- **SSH ключ (на сервере):** `~/.ssh/brain_vps`
- **Пользователь itfresh:** `ssh itfresh@212.69.85.169` (пароль: `Itfresh2012!!!`)

## Проект AdminDB

- **URL:** https://adminbd.itfresh.ru
- **Admin логин:** admin / `O-t9nW-FVhxxW-LCGqJByg`
- **Расположение на сервере:** `/opt/admindb/`
- **Frontend исходники:** `/opt/admindb/frontend-src/src/` (React + Vite + TypeScript)
- **Frontend dist:** `/opt/admindb/frontend/dist/`
- **Backend:** `/opt/admindb/backend/` (FastAPI + PostgreSQL)
- **Docker:** `cd /opt/admindb/deploy && docker compose ps`

### Сборка фронтенда

```bash
ssh root@212.69.85.169
docker run --rm -v /opt/admindb/frontend-src:/app -w /app node:20-alpine sh -c 'npm run build 2>&1'
cp -r /opt/admindb/frontend-src/dist/. /opt/admindb/frontend/dist/
cd /opt/admindb/deploy && docker compose restart nginx
```

### Деплой бэкенда

```bash
ssh root@212.69.85.169
cd /opt/admindb/deploy && docker compose restart backend
```

## GitHub

- **Репо:** https://github.com/itfresh2025/Brain
- **Git на сервере:** `/home/itfresh/agent-second-brain/`
- **Пуш:** `GIT_SSH_COMMAND='ssh -i ~/.ssh/github_brain' git -C /home/itfresh/agent-second-brain push`
- **Правило:** любые изменения по любому проекту — коммит и пуш в этот репозиторий

## Структура репо

```
admindb/
  backend/    — FastAPI приложение
  frontend/   — скомпилированный dist
  deploy/     — docker-compose, nginx, .env
Brain/        — заметки и документация
```
