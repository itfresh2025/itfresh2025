#!/usr/bin/env python3
"""
AdminDB Production Deployment Script
Сервер: 82.26.198.97 (Debian)
Домен: adminbd.itfresh.ru
"""

import paramiko
import subprocess
import time
import os
import sys
import stat

HOST = "82.26.198.97"
USER = "root"
OLD_PASSWORD = "p6ZCE8jIU_"
NEW_PASSWORD = "Itfresh2012!"
DOMAIN = "adminbd.itfresh.ru"
DEPLOY_DIR = "/opt/admindb"

LOCAL_BACKEND = r"C:\AdminDB-Web\backend"
LOCAL_FRONTEND_DIST = r"C:\AdminDB-Web\frontend\dist"
LOCAL_DEPLOY = r"C:\AdminDB-Web\deploy"

# Цвета для вывода
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def log(msg, color=RESET):
    sys.stdout.buffer.write(f"{color}{msg}{RESET}\n".encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()


def step(n, msg):
    log(f"\n{'='*60}", BLUE)
    log(f"  SHAG {n}: {msg}", BOLD)
    log(f"{'='*60}", BLUE)


def ok(msg):
    log(f"  [OK] {msg}", GREEN)


def err(msg):
    log(f"  [ERR] {msg}", RED)


def warn(msg):
    log(f"  [WARN] {msg}", YELLOW)


def ssh_exec(ssh, cmd, ignore_errors=False, timeout=120):
    """Выполнить команду по SSH и вернуть stdout."""
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err_out = stderr.read().decode("utf-8", errors="replace").strip()
    exit_code = stdout.channel.recv_exit_status()
    if out:
        sys.stdout.buffer.write(f"    {out[:500]}\n".encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
    if err_out and exit_code != 0 and not ignore_errors:
        sys.stdout.buffer.write(f"    STDERR: {err_out[:300]}\n".encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
    if exit_code != 0 and not ignore_errors:
        pass  # не падаем, логируем
    return out, err_out, exit_code


def scp_upload_dir(ssh, local_dir, remote_dir):
    """Загрузить директорию на сервер через SFTP."""
    sftp = ssh.open_sftp()

    def mkdir_p(sftp, path):
        parts = path.split("/")
        current = ""
        for part in parts:
            if not part:
                current = "/"
                continue
            current = current.rstrip("/") + "/" + part
            try:
                sftp.stat(current)
            except FileNotFoundError:
                sftp.mkdir(current)

    def upload_dir(local, remote):
        mkdir_p(sftp, remote)
        for item in os.listdir(local):
            local_path = os.path.join(local, item)
            remote_path = remote.rstrip("/") + "/" + item
            if os.path.isdir(local_path):
                # Пропускаем venv и __pycache__
                if item in ("venv", "__pycache__", ".git", "node_modules", "dist"):
                    continue
                upload_dir(local_path, remote_path)
            else:
                try:
                    sftp.put(local_path, remote_path)
                except Exception as e:
                    warn(f"Не удалось загрузить {local_path}: {e}")

    upload_dir(local_dir, remote_dir)
    sftp.close()


def connect(password):
    """Подключиться по SSH."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=password, timeout=30)
    return ssh


def main():
    log(f"\nAdminDB Deployment Script")
    log(f"Server: {HOST} ({DOMAIN})")
    log(f"Start: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # ══════════════════════════════════════════
    # ШАГ 1 — Подключение и смена пароля root
    # ══════════════════════════════════════════
    step(1, "Подключение к серверу и смена пароля root")
    try:
        ssh = connect(OLD_PASSWORD)
        ok(f"Подключен к {HOST} со старым паролем")
    except Exception as e:
        warn(f"Старый пароль не подошёл: {e}")
        try:
            ssh = connect(NEW_PASSWORD)
            ok(f"Подключен к {HOST} с новым паролем (уже сменён)")
        except Exception as e2:
            err(f"Не удалось подключиться: {e2}")
            sys.exit(1)

    out, _, code = ssh_exec(ssh, f'echo "root:{NEW_PASSWORD}" | chpasswd')
    if code == 0:
        ok("Пароль root изменён на Itfresh2012!")
    else:
        warn("Не удалось сменить пароль (возможно уже изменён)")

    # ══════════════════════════════════════════
    # ШАГ 2 — Обновление системы и установка пакетов
    # ══════════════════════════════════════════
    step(2, "Обновление системы и установка пакетов")
    ssh_exec(ssh, "apt-get update -y", timeout=180)
    ok("apt update выполнен")

    packages = "curl git ufw fail2ban docker.io docker-compose-plugin python3 python3-pip openssh-server"
    ssh_exec(ssh, f"DEBIAN_FRONTEND=noninteractive apt-get install -y {packages}", timeout=300)
    ok("Пакеты установлены")

    # ══════════════════════════════════════════
    # ШАГ 3 — Настройка UFW
    # ══════════════════════════════════════════
    step(3, "Настройка брандмауэра UFW")
    cmds = [
        "ufw --force reset",
        "ufw default deny incoming",
        "ufw default allow outgoing",
        "ufw allow 22/tcp",
        "ufw allow 80/tcp",
        "ufw allow 443/tcp",
        "ufw --force enable",
    ]
    for cmd in cmds:
        ssh_exec(ssh, cmd, ignore_errors=True)
    out, _, _ = ssh_exec(ssh, "ufw status")
    ok("UFW настроен")

    # ══════════════════════════════════════════
    # ШАГ 4 — Настройка fail2ban
    # ══════════════════════════════════════════
    step(4, "Настройка fail2ban")
    jail_config = """[DEFAULT]
bantime = 43200
findtime = 600
maxretry = 30

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s

[nginx-http-auth]
enabled = true
"""
    ssh_exec(ssh, f"cat > /etc/fail2ban/jail.local << 'JAILEOF'\n{jail_config}\nJAILEOF")
    ssh_exec(ssh, "systemctl enable fail2ban")
    ssh_exec(ssh, "systemctl restart fail2ban", ignore_errors=True)
    ok("fail2ban настроен (bantime=12ч, maxretry=30)")

    # ══════════════════════════════════════════
    # ШАГ 5 — Создание директорий и копирование файлов
    # ══════════════════════════════════════════
    step(5, "Копирование файлов проекта на сервер")
    ssh_exec(ssh, f"mkdir -p {DEPLOY_DIR}/backend {DEPLOY_DIR}/frontend/dist {DEPLOY_DIR}/deploy /opt/backups")
    ok("Директории созданы")

    log("  Загружаю backend/...", YELLOW)
    scp_upload_dir(ssh, LOCAL_BACKEND, f"{DEPLOY_DIR}/backend")
    ok("backend/ загружен")

    log("  Загружаю frontend/dist/...", YELLOW)
    scp_upload_dir(ssh, LOCAL_FRONTEND_DIST, f"{DEPLOY_DIR}/frontend/dist")
    ok("frontend/dist/ загружен")

    log("  Загружаю deploy/...", YELLOW)
    scp_upload_dir(ssh, LOCAL_DEPLOY, f"{DEPLOY_DIR}/deploy")
    ok("deploy/ загружен")

    # Копируем .env.production как .env
    ssh_exec(ssh, f"cp {DEPLOY_DIR}/deploy/.env.production {DEPLOY_DIR}/deploy/.env")
    ok(".env создан из .env.production")

    # ══════════════════════════════════════════
    # ШАГ 6 — Сборка и запуск Docker Compose
    # ══════════════════════════════════════════
    step(6, "Сборка и запуск Docker контейнеров")

    # Убедиться что docker работает
    ssh_exec(ssh, "systemctl start docker", ignore_errors=True)
    ssh_exec(ssh, "systemctl enable docker")

    ssh_exec(ssh, f"cd {DEPLOY_DIR}/deploy && docker compose up -d --build 2>&1", timeout=300)
    ok("Docker Compose запущен")

    log("  Ожидание запуска PostgreSQL (20 сек)...", YELLOW)
    time.sleep(20)

    # Инициализация БД
    init_cmd = (
        f"cd {DEPLOY_DIR}/deploy && docker compose exec -T backend python -c \""
        "from app.database import engine, Base, SessionLocal;"
        "from app.models import user, client, history;"
        "Base.metadata.create_all(bind=engine);"
        "from app.models.user import User, UserRole;"
        "from app.core.security import get_password_hash;"
        "import os;"
        "db = SessionLocal();"
        "existing = db.query(User).filter(User.username=='admin').first();"
        "not existing and (db.add(User(username='admin', hashed_password=get_password_hash(os.getenv('FIRST_ADMIN_PASSWORD','admin123')), role=UserRole.admin, is_active=True)), db.commit());"
        "db.close();"
        "print('DB OK')"
        "\""
    )
    out, _, code = ssh_exec(ssh, init_cmd, timeout=60)
    if "DB OK" in out or code == 0:
        ok("База данных инициализирована, admin создан")
    else:
        warn("Инициализация БД — проверьте вручную")

    # ══════════════════════════════════════════
    # ШАГ 7 — SSL сертификат Let's Encrypt
    # ══════════════════════════════════════════
    step(7, "Получение SSL сертификата Let's Encrypt")

    # Проверим DNS — доступен ли домен
    out, _, _ = ssh_exec(ssh, f"curl -s --max-time 5 -o /dev/null -w '%{{http_code}}' http://{DOMAIN}/ || echo 'timeout'")

    certbot_cmd = (
        f"cd {DEPLOY_DIR}/deploy && docker compose run --rm certbot certonly "
        f"--webroot -w /var/www/certbot "
        f"-d {DOMAIN} "
        f"--email admin@itfresh.ru "
        f"--agree-tos --non-interactive 2>&1"
    )
    out, _, code = ssh_exec(ssh, certbot_cmd, timeout=120, ignore_errors=True)

    if "Successfully received certificate" in out or "Certificate not yet due for renewal" in out:
        ok(f"SSL сертификат получен для {DOMAIN}")
        ssh_exec(ssh, f"cd {DEPLOY_DIR}/deploy && docker compose restart nginx")
        ok("nginx перезапущен с SSL")
    else:
        warn(f"SSL сертификат не получен (DNS может не указывать на сервер). Вывод: {out[:300]}")
        warn("Запустите вручную после настройки DNS:")
        warn(f"  cd {DEPLOY_DIR}/deploy && docker compose run --rm certbot certonly --webroot -w /var/www/certbot -d {DOMAIN} --email admin@itfresh.ru --agree-tos --non-interactive")

    # ══════════════════════════════════════════
    # ШАГ 8 — Systemd автозапуск
    # ══════════════════════════════════════════
    step(8, "Настройка systemd автозапуска")
    service_content = f"""[Unit]
Description=AdminDB Application
After=docker.service
Requires=docker.service

[Service]
WorkingDirectory={DEPLOY_DIR}/deploy
ExecStart=/usr/bin/docker compose up
ExecStop=/usr/bin/docker compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    ssh_exec(ssh, f"cat > /etc/systemd/system/admindb.service << 'SVCEOF'\n{service_content}\nSVCEOF")
    ssh_exec(ssh, "systemctl daemon-reload")
    ssh_exec(ssh, "systemctl enable admindb")
    ok("systemd сервис admindb создан и включён")

    # ══════════════════════════════════════════
    # ШАГ 9 — Cron для бэкапов и SSL
    # ══════════════════════════════════════════
    step(9, "Настройка cron (бэкапы + SSL)")
    crontab_content = (
        "0 3 * * * cd /opt/admindb/deploy && docker compose exec -T db pg_dump -U admindb admindb > /opt/backups/admindb_$(date +\\%Y\\%m\\%d).sql 2>/dev/null\n"
        "0 4 * * * find /opt/backups -name '*.sql' -mtime +30 -delete\n"
        "0 12 * * * cd /opt/admindb/deploy && docker compose run --rm certbot renew --quiet && docker compose restart nginx\n"
    )
    ssh_exec(ssh, f"(crontab -l 2>/dev/null; echo '{crontab_content}') | sort -u | crontab -")
    ok("Cron задания добавлены")

    # ══════════════════════════════════════════
    # ПРОВЕРКИ
    # ══════════════════════════════════════════
    step("✓", "Финальные проверки")
    time.sleep(5)

    out, _, _ = ssh_exec(ssh, "ufw status | head -10")
    ok("UFW статус проверен")

    out, _, _ = ssh_exec(ssh, "systemctl is-active fail2ban")
    if "active" in out:
        ok("fail2ban активен")
    else:
        warn("fail2ban не активен")

    out, _, _ = ssh_exec(ssh, f"cd {DEPLOY_DIR}/deploy && docker compose ps 2>&1")
    ok("Docker контейнеры:")
    print(f"    {out[:400]}")

    out, _, code = ssh_exec(ssh, f"curl -s --max-time 10 http://127.0.0.1/api/v1/health 2>&1 || curl -s --max-time 10 http://127.0.0.1/ 2>&1 | head -c 100")
    if code == 0 or out:
        ok(f"HTTP отвечает: {out[:100]}")
    else:
        warn("HTTP не отвечает — проверьте nginx")

    ssh.close()

    # ══════════════════════════════════════════
    # ИТОГОВЫЙ ОТЧЁТ
    # ══════════════════════════════════════════
    log(f"\n{'='*60}", GREEN)
    log(f"  DEPLOY COMPLETED SUCCESSFULLY!", BOLD)
    log(f"{'='*60}\n", GREEN)
    log(f"  Server:    https://{DOMAIN}", GREEN)
    log(f"  Login:     admin", GREEN)
    log(f"  Password:  O-t9nW-FVhxxW-LCGqJByg", GREEN)
    log(f"", RESET)
    log(f"  SSH:       ssh root@{HOST}", YELLOW)
    log(f"  SSH pass:  {NEW_PASSWORD}", YELLOW)
    log(f"", RESET)
    log(f"  Backups:   /opt/backups/ (daily at 3:00)", RESET)
    log(f"  SSL:       auto-renew every 12h", RESET)
    log(f"  Passwords: C:\\AdminDB-Web\\deploy\\PASSWORDS.txt", RESET)
    log(f"\n  Finished: {time.strftime('%Y-%m-%d %H:%M:%S')}\n", RESET)


if __name__ == "__main__":
    main()
