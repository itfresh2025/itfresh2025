#!/bin/bash
# Запустить ОДИН РАЗ на сервере (root@212.69.85.169):
# bash setup_github_autosync.sh
#
# Настраивает автоматический пуш в GitHub каждые 5 минут
# если есть незапушенные коммиты.

set -e

REPO="/home/itfresh/agent-second-brain"
KEY="/home/itfresh/.ssh/github_brain"

# Создаём скрипт синка
cat > /usr/local/bin/sync-brain-to-github << 'SCRIPT'
#!/bin/bash
REPO="/home/itfresh/agent-second-brain"
KEY="/home/itfresh/.ssh/github_brain"
LOG="/var/log/github-sync.log"

cd "$REPO" || exit 1

# Проверяем есть ли что пушить
LOCAL=$(git rev-parse HEAD 2>/dev/null)
REMOTE=$(GIT_SSH_COMMAND="ssh -i $KEY -o StrictHostKeyChecking=no" git ls-remote origin HEAD 2>/dev/null | awk '{print $1}')

if [ "$LOCAL" != "$REMOTE" ] && [ -n "$LOCAL" ]; then
    GIT_SSH_COMMAND="ssh -i $KEY -o StrictHostKeyChecking=no" git push origin main >> "$LOG" 2>&1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pushed to GitHub: $LOCAL" >> "$LOG"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Already in sync" >> "$LOG"
fi
SCRIPT

chmod +x /usr/local/bin/sync-brain-to-github

# Добавляем в cron (каждые 5 минут, от пользователя itfresh)
(crontab -u itfresh -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/sync-brain-to-github") | sort -u | crontab -u itfresh -

echo "✓ Автосинк настроен. Каждые 5 минут изменения пушатся в GitHub."
echo "  Логи: /var/log/github-sync.log"
echo "  Проверить: crontab -u itfresh -l"
