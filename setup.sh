#!/bin/bash
# ============================================================
# Debian VM — Web Server Setup Script
# Author: itfresh2025
# Stack: Nginx + Certbot (Let's Encrypt) + UFW + fail2ban
# Usage: sudo bash setup.sh <your-domain.com>
# ============================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

DOMAIN="${1:-}"
WEB_DIR="/var/www/${DOMAIN:-site}"
NGINX_CONF="/etc/nginx/sites-available/${DOMAIN:-site}"

log()   { echo -e "${GREEN}[✔]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✘]${NC} $1"; exit 1; }
info()  { echo -e "${CYAN}[→]${NC} $1"; }

banner() {
  echo -e "${BLUE}"
  echo "╔══════════════════════════════════════════════╗"
  echo "║        Debian VM Web Setup — itfresh2025     ║"
  echo "╚══════════════════════════════════════════════╝"
  echo -e "${NC}"
}

check_root() {
  [[ $EUID -ne 0 ]] && error "Run as root: sudo bash setup.sh <domain>"
}

check_domain() {
  [[ -z "$DOMAIN" ]] && error "Provide domain: sudo bash setup.sh example.com"
  info "Domain: ${DOMAIN}"
}

update_system() {
  info "Updating system packages..."
  apt-get update -qq
  apt-get upgrade -y -qq
  log "System updated"
}

install_packages() {
  info "Installing nginx, certbot, ufw, fail2ban, git..."
  apt-get install -y -qq \
    nginx \
    certbot \
    python3-certbot-nginx \
    ufw \
    fail2ban \
    git \
    curl \
    unzip \
    htop \
    logrotate
  log "Packages installed"
}

configure_firewall() {
  info "Configuring UFW firewall..."
  ufw --force reset
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow 22/tcp    comment 'SSH'
  ufw allow 80/tcp    comment 'HTTP'
  ufw allow 443/tcp   comment 'HTTPS'
  ufw --force enable
  log "Firewall configured (SSH 22, HTTP 80, HTTPS 443)"
}

configure_fail2ban() {
  info "Configuring fail2ban..."
  cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port    = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
EOF
  systemctl enable fail2ban --quiet
  systemctl restart fail2ban
  log "fail2ban configured"
}

deploy_website() {
  info "Deploying website to ${WEB_DIR}..."
  mkdir -p "${WEB_DIR}"

  # Copy website files from repo directory (relative to script)
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -d "${SCRIPT_DIR}/website" ]]; then
    cp -r "${SCRIPT_DIR}/website/." "${WEB_DIR}/"
    chown -R www-data:www-data "${WEB_DIR}"
    chmod -R 755 "${WEB_DIR}"
    log "Website files deployed"
  else
    warn "website/ directory not found — creating placeholder"
    echo "<h1>Coming soon — ${DOMAIN}</h1>" > "${WEB_DIR}/index.html"
  fi
}

configure_nginx() {
  info "Configuring Nginx..."
  cat > "${NGINX_CONF}" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN} www.${DOMAIN};
    root ${WEB_DIR};
    index index.html;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml application/json
               application/javascript application/xml+rss image/svg+xml;

    # Cache static assets
    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg|woff2?|ttf)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Block hidden files
    location ~ /\. {
        deny all;
    }
}
EOF

  # Enable site
  ln -sf "${NGINX_CONF}" "/etc/nginx/sites-enabled/${DOMAIN}"
  rm -f /etc/nginx/sites-enabled/default

  nginx -t
  systemctl enable nginx --quiet
  systemctl reload nginx
  log "Nginx configured"
}

setup_ssl() {
  info "Obtaining SSL certificate via Let's Encrypt..."
  certbot --nginx \
    -d "${DOMAIN}" \
    -d "www.${DOMAIN}" \
    --non-interactive \
    --agree-tos \
    --email "admin@${DOMAIN}" \
    --redirect \
    --quiet

  # Auto-renewal cron
  (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'") | crontab -
  log "SSL certificate installed + auto-renewal configured"
}

setup_logrotate() {
  info "Configuring log rotation..."
  cat > /etc/logrotate.d/nginx-site <<EOF
${WEB_DIR}/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 \$(cat /var/run/nginx.pid) 2>/dev/null
    endscript
}
EOF
  log "Log rotation configured"
}

summary() {
  echo ""
  echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║              Setup Complete!                 ║${NC}"
  echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "  ${CYAN}Site URL:${NC}   https://${DOMAIN}"
  echo -e "  ${CYAN}Web Root:${NC}   ${WEB_DIR}"
  echo -e "  ${CYAN}Nginx:${NC}      ${NGINX_CONF}"
  echo -e "  ${CYAN}SSL:${NC}        Let's Encrypt (auto-renew)"
  echo -e "  ${CYAN}Firewall:${NC}   UFW (22, 80, 443)"
  echo -e "  ${CYAN}Brute-force:${NC} fail2ban"
  echo ""
}

main() {
  banner
  check_root
  check_domain
  update_system
  install_packages
  configure_firewall
  configure_fail2ban
  deploy_website
  configure_nginx
  setup_ssl
  setup_logrotate
  summary
}

main
