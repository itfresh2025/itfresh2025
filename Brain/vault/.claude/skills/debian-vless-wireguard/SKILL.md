# OpenConnect + VLESS: прозрачный VPN-шлюз на Debian 12

Настройка сервера Debian 12 как прозрачного VPN-шлюза.
Клиент (Keenetic) подключается по **OpenConnect (AnyConnect) на порту 443** → весь TCP/UDP трафик проксируется через xray TPROXY в VLESS-туннель.

> **Почему OpenConnect, а не WireGuard?**
> WireGuard использует UDP 51820 — этот порт часто блокируется провайдером. OpenConnect работает на TCP/UDP 443, который заблокировать невозможно без отключения HTTPS.

**Финальная архитектура:**
```
Keenetic ──AnyConnect/TCP 443──▶ Debian 12 (ocserv → vpns0)
                                        │
                              iptables mangle TPROXY
                              цепочка OCVPN (i: vpns+)
                                        │
                                  xray :12345
                               (dokodemo-door tproxy)
                                        │
                                  xray VLESS out
                             (mark=255, mux=false)
                                        │
                            sudvless.example.ru:443
                                        │
                                     Интернет
                                (IP выходного узла)
```

---

## Содержание

1. [Подключение с Windows через py -3 + paramiko](#1-подключение-с-windows)
2. [Первое подключение к свежему серверу](#2-первое-подключение-к-свежему-серверу)
3. [Подготовка системы](#3-подготовка-системы)
4. [Установка и конфиг xray](#4-установка-xray)
5. [Установка и конфиг ocserv (OpenConnect)](#5-установка-ocserv)
6. [iptables TPROXY для OpenConnect](#6-iptables-tproxy)
7. [Маршрутизация fwmark (критично!)](#7-маршрутизация-fwmark)
8. [Персистентность при перезагрузке](#8-персистентность)
9. [Диагностика](#9-диагностика)
10. [Типичные ошибки](#10-типичные-ошибки)
11. [WireGuard (запасной вариант)](#11-wireguard-запасной-вариант)
12. [Параметры текущей установки](#12-параметры-текущей-установки)

---

## 1. Подключение с Windows

### Почему py -3 + paramiko

На Windows (Git Bash / MSYS2 / PowerShell):
- `python3` может возвращать exit code 49 из-за кодировки консоли (cp1251)
- `sshpass` не входит в стандартные пакеты Windows
- `plink.exe` требует принятия host key интерактивно

**Решение: `py -3` + paramiko + принудительный UTF-8**

### Шаблон подключения

```python
# -*- coding: utf-8 -*-
import sys, time, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import paramiko

HOST = "1.2.3.4"
PASS = "пароль"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username='root', password=PASS, timeout=15,
          allow_agent=False, look_for_keys=False)

def run(cmd, timeout=60):
    print(f'\n>>> {cmd}')
    _, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out: print(out)
    if err: print(f'[ERR] {err[:400]}')
    return out

def write_file(path, content):
    """Запись файла через SFTP — избегает проблем с heredoc, JSON, спецсимволами."""
    sftp = c.open_sftp()
    with sftp.open(path, 'w') as f:
        f.write(content)
    sftp.close()
    print(f'[SFTP] {path} ({len(content)} байт)')
```

**Запуск:**
```cmd
py -3 "C:/my_script.py"
```

> ⚠️ Всегда абсолютный путь: `py -3 "C:/path/script.py"` — не относительный.
> Рабочая директория в cmd может быть `C:\Windows\system32`, Python не найдёт файл без полного пути.

**Запись файлов на сервер — только через SFTP:**
```python
# ПРАВИЛЬНО — SFTP:
write_file("/etc/ocserv/ocserv.conf", conf_content)
write_file("/usr/local/etc/xray/config.json", json.dumps(xray_config, indent=2))

# НЕПРАВИЛЬНО — heredoc ломается на JSON, спецсимволах (!, $, кавычки):
run(f"cat > /etc/file << 'EOF'\n{content}\nEOF")  # ❌
```

---

## 2. Первое подключение к свежему серверу

### PasswordAuthentication отключён (Debian 12)

Свежий Debian 12 VPS **по умолчанию отключает вход по паролю**:
```
paramiko.ssh_exception.AuthenticationException: Authentication failed.
# или
Bad authentication type; allowed types: ['publickey']
```

**Решение:** зайди через консоль хостинга (VNC/KVM) и выполни:
```bash
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
# Если строки нет — добавь:
echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config
systemctl restart sshd
```

После этого paramiko-подключение по паролю работает.

### Истёкший пароль (Password change required)

Если провайдер выдал пароль со статусом "необходимо сменить":
```
WARNING: Your password has expired.
Password change required but no TTY available.
```

`exec_command` не даёт TTY — нужен `invoke_shell()`:
```python
def change_expired_password(host, old_pass, new_pass):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, username='root', password=old_pass, timeout=15,
              allow_agent=False, look_for_keys=False)
    chan = c.invoke_shell()
    time.sleep(1)
    out = chan.recv(4096).decode(errors='replace')
    if 'current' in out.lower() or 'password' in out.lower():
        chan.send(old_pass + '\n'); time.sleep(1); chan.recv(4096)
        chan.send(new_pass + '\n'); time.sleep(1); chan.recv(4096)
        chan.send(new_pass + '\n'); time.sleep(1); chan.recv(4096)
    chan.close()
    c.close()
```

---

## 3. Подготовка системы

```python
# Базовые пакеты (ocserv включён)
run('DEBIAN_FRONTEND=noninteractive apt-get update -q', timeout=60)
run('DEBIAN_FRONTEND=noninteractive apt-get install -y '
    'curl wget unzip iptables-persistent net-tools ocserv gnutls-bin openssl '
    '2>&1 | tail -5', timeout=180)

# IP forwarding
run("echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf && sysctl -p")

# BBR + буферы
run("modprobe tcp_bbr && echo tcp_bbr >> /etc/modules-load.d/modules.conf")
run("""cat >> /etc/sysctl.conf << 'EOF'
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq
EOF""")
run('sysctl -p')
```

---

## 4. Установка xray

### Установка

```python
run('bash -c "$(curl -fsSL https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install',
    timeout=120)
run('xray version 2>&1 | head -1')
```

Устанавливается в `/usr/local/bin/xray`, конфиг в `/usr/local/etc/xray/config.json`.

### Конфиг xray

```python
import json

VLESS_UUID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
VLESS_HOST = "sudvless.example.ru"
VLESS_IP   = "202.148.54.236"   # IP VLESS сервера — исключить из проксирования!

XRAY_CONFIG = {
    "log": {"loglevel": "warning"},
    "inbounds": [
        {
            "tag": "socks-in",
            "port": 10808,
            "listen": "127.0.0.1",
            "protocol": "socks",
            "settings": {"auth": "noauth", "udp": True}
        },
        {
            "tag": "tproxy-in",
            "port": 12345,
            "listen": "0.0.0.0",
            "protocol": "dokodemo-door",
            "settings": {"network": "tcp,udp", "followRedirect": True},
            "streamSettings": {"sockopt": {"tproxy": "tproxy"}},
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls", "quic"]
            }
        }
    ],
    "outbounds": [
        {
            "tag": "vless-out",
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": VLESS_HOST,
                    "port": 443,
                    "users": [{"id": VLESS_UUID, "encryption": "none", "flow": ""}]
                }]
            },
            "streamSettings": {
                "network": "tcp",
                "security": "tls",
                "tlsSettings": {
                    "serverName": VLESS_HOST,
                    "fingerprint": "chrome",
                    "alpn": ["h2", "http/1.1"]
                },
                "sockopt": {
                    "mark": 255,            # исходящий xray трафик не попадёт в TPROXY
                    "domainStrategy": "UseIP"
                }
            },
            # mux=false — обязательно на VPS с 1 CPU без AES-NI
            # mux добавляет overhead TLS-поверх-TLS → x17 деградация на слабом VPS
            "mux": {"enabled": False, "concurrency": 8}
        },
        {"tag": "direct", "protocol": "freedom"},
        {"tag": "block", "protocol": "blackhole"}
    ],
    "routing": {
        "domainStrategy": "AsIs",
        "rules": [
            {
                "type": "field",
                "ip": ["geoip:private", VLESS_IP],  # прямо, без петли
                "outboundTag": "direct"
            },
            {
                "type": "field",
                "protocol": ["bittorrent"],
                "outboundTag": "block"
            }
        ]
    }
}

write_file("/usr/local/etc/xray/config.json",
           json.dumps(XRAY_CONFIG, indent=2, ensure_ascii=False))
```

### Systemd override (CAP_NET_ADMIN для tproxy)

```python
XRAY_OVERRIDE = """\
[Service]
User=root
Group=root
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
"""
run("mkdir -p /etc/systemd/system/xray.service.d/")
write_file("/etc/systemd/system/xray.service.d/tproxy-caps.conf", XRAY_OVERRIDE)
run("systemctl daemon-reload && systemctl enable xray && systemctl restart xray")
```

### Проверка xray

```bash
systemctl is-active xray
# Тест через SOCKS5 — должен вернуть IP VLESS-узла, не IP сервера:
curl -s --socks5 127.0.0.1:10808 --max-time 15 https://ifconfig.me
```

---

## 5. Установка ocserv

### Сертификат (самоподписанный)

```python
run('mkdir -p /etc/ocserv/ssl')
run(
    'openssl req -x509 -newkey rsa:2048 '
    '-keyout /etc/ocserv/ssl/server-key.pem '
    '-out /etc/ocserv/ssl/server-cert.pem '
    '-days 3650 -nodes '
    f'-subj "/CN={HOST}" 2>&1'
)
```

### Конфиг ocserv

```python
OCSERV_CONF = f"""auth = "plain[passwd=/etc/ocserv/ocpasswd]"
tcp-port = 443
udp-port = 443
server-cert = /etc/ocserv/ssl/server-cert.pem
server-key = /etc/ocserv/ssl/server-key.pem
ca-cert = /etc/ocserv/ssl/server-cert.pem
socket-file = /var/run/ocserv-socket
run-as-user = nobody
run-as-group = daemon
device = vpns
ipv4-network = 192.168.8.0/24
ipv4-netmask = 255.255.255.0
dns = 8.8.8.8
dns = 8.8.4.4
route = default
no-route = {HOST}/255.255.255.255
no-route = {VLESS_IP}/255.255.255.255
max-clients = 16
max-same-clients = 4
keepalive = 30
dpd = 60
mobile-dpd = 300
try-mtu-discovery = true
compression = true
tls-priorities = "NORMAL:%SERVER_PRECEDENCE:%COMPAT:-VERS-SSL3.0"
auth-timeout = 240
idle-timeout = 1200
session-timeout = 86400
"""
write_file('/etc/ocserv/ocserv.conf', OCSERV_CONF)
```

> ⚠️ **`device = vpns`** — именно так, без `%d`. ocserv сам добавляет номер к имени интерфейса (vpns0, vpns1...).
> Если написать `device = vpns%d` — ocserv подставит ещё один `%d` → `vpns%d%d: TUNSETIFF: Invalid argument`.
>
> ⚠️ Не добавляй опции `net-proto` и `ping-leases-time` — они не существуют в текущей версии ocserv и вызывают предупреждения.

### Создание пользователя

```python
run('echo "ПарольПользователя" | ocpasswd -c /etc/ocserv/ocpasswd username')
run('cat /etc/ocserv/ocpasswd')  # проверка
```

### Запуск ocserv

```python
run('systemctl enable ocserv')
run('systemctl restart ocserv')
time.sleep(3)
run('systemctl status ocserv --no-pager -l')
run('ss -tlnp | grep 443')
run('ss -ulnp | grep 443')
```

### Данные для подключения Keenetic

```
Тип:       Cisco AnyConnect / OpenConnect
Сервер:    155.212.159.202
Порт:      443
Логин:     itfresh
Пароль:    Itfresh2012
```

В Keenetic: **Интернет → Другие подключения → AnyConnect → Добавить**

---

## 6. iptables TPROXY

Интерфейс OpenConnect — `vpns+` (wildcard для vpns0, vpns1 и т.д.).
Цепочку назовём `OCVPN` (отдельно от `XRAY` для WireGuard).

```python
iface = run("ip route show default | awk '{print $5}' | head -1")  # eth0

# Сброс старых правил (ВСЕГДА перед добавлением новых!)
flush_cmds = [
    'iptables -t mangle -F XRAY 2>/dev/null || true',
    'iptables -t mangle -X XRAY 2>/dev/null || true',
    'iptables -t mangle -D PREROUTING -i wg0 -j XRAY 2>/dev/null || true',
    'iptables -t mangle -F OCVPN 2>/dev/null || true',
    'iptables -t mangle -X OCVPN 2>/dev/null || true',
    'iptables -t mangle -D PREROUTING -i vpns+ -j OCVPN 2>/dev/null || true',
    'iptables -t nat -F POSTROUTING',
    'iptables -F FORWARD',
]
for cmd in flush_cmds:
    run(cmd)

# Новая цепочка OCVPN
run('iptables -t mangle -N OCVPN')

# Исключения — не проксировать частные сети и VLESS-сервер
for net in ['0.0.0.0/8', '10.0.0.0/8', '127.0.0.0/8',
            '169.254.0.0/16', '172.16.0.0/12', '192.168.0.0/16',
            '224.0.0.0/4', '240.0.0.0/4']:
    run(f'iptables -t mangle -A OCVPN -d {net} -j RETURN')
run(f'iptables -t mangle -A OCVPN -d {VLESS_IP}/32 -j RETURN')

# TCP + UDP → TPROXY → xray :12345, пометить fwmark=1
run('iptables -t mangle -A OCVPN -p tcp -j TPROXY --on-port 12345 --tproxy-mark 1')
run('iptables -t mangle -A OCVPN -p udp -j TPROXY --on-port 12345 --tproxy-mark 1')

# Применить к vpns+ (OpenConnect интерфейс)
run('iptables -t mangle -A PREROUTING -i vpns+ -j OCVPN')

# NAT + FORWARD + MSS clamping
run(f'iptables -t nat -A POSTROUTING -o {iface} -j MASQUERADE')
run('iptables -A FORWARD -i vpns+ -j ACCEPT')
run(f'iptables -t mangle -A FORWARD -i vpns+ -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu')
run(f'iptables -t mangle -A POSTROUTING -o {iface} -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu')

# Сохранить
run('iptables-save > /etc/iptables/rules.v4 && echo SAVED')
```

> ⚠️ **TPROXY работает только в PREROUTING**, не в OUTPUT или FORWARD.
> ⚠️ `sockopt.mark: 255` в outbound xray — исходящие пакеты xray не попадут обратно в TPROXY (у них fwmark≠1).

---

## 7. Маршрутизация fwmark (критично!)

Без этих правил TPROXY пакеты будут отброшены ядром — Keenetic получит IP, но трафик не пройдёт.

```bash
ip rule add fwmark 1 table 100
ip route add local default dev lo table 100
```

**Проверка:**
```bash
ip rule show | grep fwmark
# → 32765: from all fwmark 0x1 lookup 100

ip route show table 100
# → local default dev lo scope host
```

**Критическая ловушка:** если раньше использовался WireGuard с `wg-quick`, его `PreDown` hook **удаляет** эти правила:
```
PreDown = ip rule del fwmark 1 table 100 ...
```

После `systemctl stop wg-quick@wg0` правила исчезают. Для OpenConnect их нужно восстановить вручную и через скрипт персистентности.

**Диагностика пропавшего fwmark:**
```bash
# Симптом: Keenetic подключается (vpns0 UP, IP выдан), но через 16 сек сессия обрывается
# journalctl -u ocserv: "sec-mod: invalidating session of user 'itfresh'"
# Причина: TPROXY пакеты не доставляются, ответов нет → таймаут

ip rule show | grep fwmark   # пусто → вот причина
ip route show table 100      # пусто → вот причина

# Лечение:
ip rule add fwmark 1 table 100
ip route add local default dev lo table 100
# После этого xray немедленно начнёт логировать: "accepted tcp:... [tproxy-in >> vless-out]"
```

**Дублирующиеся правила fwmark:**
```bash
ip rule show | grep fwmark
# 32764: from all fwmark 0x1 lookup 100
# 32765: from all fwmark 0x1 lookup 100   ← дубль

# Удалить один:
ip rule del fwmark 1 table 100   # удаляет первый найденный
ip rule show | grep fwmark       # проверить — должна остаться одна строка
```

---

## 8. Персистентность

### tproxy-route (для fwmark)

```python
TPROXY_ROUTE = """\
#!/bin/bash
ip rule add fwmark 1 table 100 2>/dev/null || true
ip route add local default dev lo table 100 2>/dev/null || true
"""
run('mkdir -p /etc/network/if-up.d')
write_file('/etc/network/if-up.d/tproxy-route', TPROXY_ROUTE)
run('chmod +x /etc/network/if-up.d/tproxy-route')
run('/etc/network/if-up.d/tproxy-route')
```

### iptables-persistent (для правил iptables)

```bash
iptables-save > /etc/iptables/rules.v4
# При установке iptables-persistent спросит сохранить ли правила — ответить Yes
systemctl enable netfilter-persistent
```

### Итоговые файлы на сервере

| Файл | Назначение |
|---|---|
| `/usr/local/etc/xray/config.json` | xray: SOCKS5 + tproxy-in + VLESS outbound |
| `/etc/systemd/system/xray.service.d/tproxy-caps.conf` | Override: root + CAP_NET_ADMIN |
| `/etc/ocserv/ocserv.conf` | OpenConnect сервер |
| `/etc/ocserv/ssl/server-cert.pem` | Самоподписанный TLS-сертификат |
| `/etc/ocserv/ocpasswd` | Пароли пользователей ocserv |
| `/etc/iptables/rules.v4` | iptables mangle OCVPN + NAT + FORWARD |
| `/etc/network/if-up.d/tproxy-route` | ip rule/route при перезагрузке |
| `/etc/sysctl.conf` | ip_forward + BBR + буферы 16MB |

---

## 9. Диагностика

### Быстрая проверка всей цепочки

```bash
# 1. Статус сервисов
systemctl is-active ocserv xray

# 2. Порты
ss -tlnp | grep 443        # ocserv слушает TCP 443
ss -ulnp | grep 443        # ocserv слушает UDP 443
ss -tlnp | grep 10808      # xray SOCKS5

# 3. Клиент подключён?
ip addr show vpns0         # интерфейс UP, peer IP клиента
# inet 192.168.8.1 peer 192.168.8.80/32 scope global vpns0

# 4. xray принимает трафик?
journalctl -u xray -n 20 --no-pager
# Должно быть: "from 192.168.8.80:XXXXX accepted tcp:...:443 [tproxy-in >> vless-out]"

# 5. Счётчики TPROXY
iptables -t mangle -L OCVPN -v -n | grep TPROXY
# pkts > 0 — трафик идёт в xray

# 6. Маршрутизация fwmark
ip rule show | grep fwmark           # должна быть одна строка
ip route show table 100              # local default dev lo scope host

# 7. VLESS работает напрямую с сервера
curl -s --socks5 127.0.0.1:10808 --max-time 15 https://ifconfig.me
# Должен вернуть IP VLESS-узла (202.148.54.236), не IP сервера
```

### tcpdump — есть ли трафик от Keenetic

```bash
# Проверить что Keenetic вообще достигает сервера (не заблокировано провайдером)
timeout 30 tcpdump -i eth0 -n tcp port 443 2>/dev/null | head -20

# Если нет ни одного пакета от IP Keenetic → провайдер блокирует порт
# Если есть TLS-хендшейк → ocserv получает подключение
```

### Диагностика сессий ocserv

```bash
# Логи последних подключений
journalctl -u ocserv -n 30 --no-pager

# Нормальный флоу (успех):
# sec-mod: initiating session for user 'itfresh' (session: XXX)
# [затем в xray]: accepted tcp:... [tproxy-in >> vless-out]

# Плохой флоу (TPROXY сломан):
# sec-mod: initiating session for user 'itfresh' (session: XXX)
# sec-mod: invalidating session of user 'itfresh'  ← через 16 сек → fwmark пропал!
```

### Проверка блокировки UDP провайдером (WireGuard)

```bash
# На сервере смотрим tcpdump на eth0:
timeout 30 tcpdump -i eth0 -n udp port 51820 2>/dev/null | head -10

# Если пакеты есть → WireGuard работает, проблема в другом
# Если пакетов нет → провайдер блокирует UDP 51820 → нужен OpenConnect
```

---

## 10. Типичные ошибки

### `Bad authentication type; allowed types: ['publickey']`

**Причина:** Debian 12 по умолчанию отключает вход по паролю.
**Решение:** через VNC-консоль хостинга:
```bash
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart sshd
```

---

### `vpns%d%d: TUNSETIFF: Invalid argument`

**Причина:** в `/etc/ocserv/ocserv.conf` указано `device = vpns%d`. ocserv сам добавляет `%d` к имени → получается `vpns%d%d`.

**Решение:** исправить на `device = vpns` (без `%d`).

```bash
# Проверить и исправить:
grep 'device' /etc/ocserv/ocserv.conf
# Должно быть: device = vpns
sed -i 's/device = vpns%d/device = vpns/' /etc/ocserv/ocserv.conf
systemctl restart ocserv
```

---

### `ocserv: the 'device' configuration option must be specified!`

**Причина:** в конфиге вообще нет строки `device = ...`.
**Решение:** добавить `device = vpns` в `/etc/ocserv/ocserv.conf`.

---

### `sec-mod: invalidating session` — Keenetic отваливается через ~16 сек

**Причина:** Keenetic успешно подключается (vpns0 UP, IP выдан), но трафик не идёт → ответов нет → dpd-таймаут → ocserv закрывает сессию.

**Диагностика:**
```bash
ip rule show | grep fwmark   # если пусто — вот причина
ip route show table 100      # если пусто — вот причина
```

**Решение:**
```bash
ip rule add fwmark 1 table 100
ip route add local default dev lo table 100
# Немедленно: xray начнёт принимать трафик от Keenetic
journalctl -u xray -f
```

Чаще всего возникает после `systemctl stop wg-quick@wg0` — его `PreDown` удаляет эти правила.

---

### Дублирующиеся `ip rule fwmark` правила

**Причина:** правило добавлялось несколько раз (повторный запуск скрипта, PostUp + ручное добавление).

**Симптом:**
```bash
ip rule show | grep fwmark
# 32764: from all fwmark 0x1 lookup 100
# 32765: from all fwmark 0x1 lookup 100
```

**Решение:** удалить один лишний:
```bash
ip rule del fwmark 1 table 100  # удаляет первый найденный
ip rule show | grep fwmark      # проверить
```

Дубли не ломают работу, но засоряют таблицу маршрутизации.

---

### Дублирующиеся правила iptables

**Причина:** скрипт запускался повторно без очистки существующих правил.

**Решение:** всегда начинать с flush:
```bash
iptables -t mangle -F OCVPN 2>/dev/null || true
iptables -t mangle -X OCVPN 2>/dev/null || true
iptables -t mangle -D PREROUTING -i vpns+ -j OCVPN 2>/dev/null || true
iptables -t nat -F POSTROUTING
iptables -F FORWARD
```

**Диагностика:**
```bash
iptables -t mangle -L PREROUTING -v -n --line-numbers | grep OCVPN
# Должна быть ровно 1 строка
```

---

### TPROXY счётчик = 0, но клиент подключён

**Причина:** клиент (Keenetic) не слал TCP/UDP трафик (только VPN-хендшейк/keepalive).
**Диагностика:**
```bash
iptables -t mangle -Z   # сбросить счётчики
# ... подождать 10 сек (Keenetic должен что-то загружать) ...
iptables -t mangle -L OCVPN -v -n | grep TPROXY
# pkts > 0 → трафик идёт нормально
```

---

### `Unknown keyword: net-proto` / `Unknown keyword: ping-leases-time`

**Причина:** эти опции не существуют в ocserv.
**Решение:** удалить эти строки из `/etc/ocserv/ocserv.conf`.

---

### mux включён — скорость упала в 10-17 раз, CPU 100% sys

**Причина:** mux добавляет мультиплексирование поверх TLS. На VPS с 1 ядром и без AES-NI перегружает CPU.

**Диагностика:**
```bash
grep -o 'aes' /proc/cpuinfo | head -1   # пусто = нет AES-NI
nproc                                    # 1 = одно ядро
```

**Решение:** в `/usr/local/etc/xray/config.json`:
```json
"mux": {"enabled": false, "concurrency": 8}
```

---

### `Error reading SSH protocol banner` — paramiko не может подключиться

**Симптом:**
```
paramiko.ssh_exception.SSHException: Error reading SSH protocol banner
```

**Причина:** sshd временно не успел принять соединение — слишком много параллельных коннектов, перезагрузка sshd, или кратковременная перегрузка сервера. Это **не** значит, что сервер упал.

**Диагностика:**
```bash
# 1. Пингуется ли сервер?
ping -n 3 155.212.159.202
# Если ответы есть → сервер жив

# 2. Порт 22 открыт?
timeout 10 bash -c "echo >/dev/tcp/155.212.159.202/22" && echo "PORT OPEN" || echo "PORT CLOSED"
# PORT OPEN → sshd слушает, просто перегружен
# PORT CLOSED → sshd не запущен или файрвол
```

**Решение:** просто повторить запуск скрипта через несколько секунд — в 99% случаев помогает. При необходимости добавить retry в скрипт:
```python
import time

def ssh_connect_retry(host, password, retries=3, delay=5):
    for attempt in range(1, retries + 1):
        try:
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c.connect(host, username='root', password=password, timeout=15,
                      allow_agent=False, look_for_keys=False)
            return c
        except Exception as e:
            print(f'[attempt {attempt}/{retries}] {e}')
            if attempt < retries:
                time.sleep(delay)
    raise RuntimeError('SSH: не удалось подключиться')

c = ssh_connect_retry(HOST, PASS)
```

---

### `py -3 script.py` — файл не найден

**Причина:** относительный путь, рабочая директория — `C:\Windows\system32`.
**Решение:** `py -3 "C:/path/to/script.py"` — всегда абсолютный путь.

---

### `UnicodeEncodeError: 'charmap' codec`

**Причина:** Windows консоль cp1251.
**Решение:**
```python
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
```

---

## 11. WireGuard (запасной вариант)

> Использовать только если провайдер **не блокирует UDP 51820**.
> Проверить: `timeout 30 tcpdump -i eth0 -n udp port 51820` — если есть пакеты от Keenetic, WireGuard работает.

### Конфиг сервера `/etc/wireguard/wg0.conf`

```ini
[Interface]
MTU = 1280
Address = 10.8.0.1/24
ListenPort = 51820
PrivateKey = <SERVER_PRIVKEY>
PostUp   = ip rule add fwmark 1 table 100 2>/dev/null || true; ip route add local default dev lo table 100 2>/dev/null || true; iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE; iptables -t mangle -A FORWARD -i wg0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu
PreDown  = ip rule del fwmark 1 table 100 2>/dev/null || true; ip route del local default dev lo table 100 2>/dev/null || true; iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE; iptables -t mangle -D FORWARD -i wg0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu

[Peer]
# Keenetic
PublicKey  = <KEENETIC_PUBKEY>
AllowedIPs = 10.8.0.2/32
```

> ⚠️ `MTU = 1280` обязательно — иначе фрагментация через VLESS-туннель.
> ⚠️ После `systemctl stop wg-quick@wg0` правила fwmark удаляются PreDown — это нормально для WireGuard, но критично если одновременно используется OpenConnect.

### Конфиг Keenetic (WireGuard)

```ini
[Interface]
PrivateKey = AJ2w7frbyW4NRpHWuAEe0KuG8MmVpQr+WEETyvh1rkk=
Address = 10.8.0.2/24
DNS = 8.8.8.8
MTU = 1280

[Peer]
PublicKey = QgMaehDNQwB5UWYA8qxlhvbv0A9gqBxYQHzMbW5YCTg=
Endpoint = 155.212.159.202:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

Импорт: **Keenetic → Интернет → WireGuard → Добавить → Импорт из файла**.

---

## 12. Параметры текущей установки

| Параметр | Значение |
|---|---|
| **Debian VPS IP** | `155.212.159.202` |
| **root пароль** | `xbYhfYS9T0nP` |
| **Основной интерфейс** | `eth0` |
| **Шлюз провайдера** | `155.212.159.201` |
| **VPN-протокол** | OpenConnect (AnyConnect), порт 443 |
| **ocserv пользователь** | `itfresh` / `Itfresh2012` |
| **ocserv подсеть** | `192.168.8.0/24` |
| **IP шлюза (Debian)** | `192.168.8.1` |
| **IP клиента (Keenetic)** | `192.168.8.80` |
| **iptables chain** | `OCVPN` (перехват с `vpns+`) |
| **xray SOCKS5** | `127.0.0.1:10808` |
| **xray TPROXY** | `0.0.0.0:12345` |
| **VLESS домен** | `sudvless.itfresh.ru` |
| **VLESS IP** | `202.148.54.236` |
| **VLESS порт** | `443` (TLS) |
| **VLESS UUID** | `e6b3c9b8-ae7f-4ba2-9b7b-42c209d3baa1` |
| **TCP congestion control** | `bbr` |
| **rmem_max / wmem_max** | `16777216` (16 MB) |
| **WireGuard** | Отключён (провайдер блокирует UDP 51820) |

### Скрипты управления (Windows)

| Скрипт | Назначение |
|---|---|
| `py -3 "C:/ocserv_setup.py"` | Полная установка ocserv + iptables |
| `py -3 "C:/ocserv_check.py"` | Диагностика: ocserv + xray + TPROXY |
| `py -3 "C:/vless_diag_fix.py"` | Пересоздание правил TPROXY |
| `py -3 "C:/vless_new_setup.py"` | Установка WireGuard-варианта (если UDP 51820 открыт) |
