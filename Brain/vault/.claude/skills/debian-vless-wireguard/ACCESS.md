# Доступы и ключи — VPN-шлюз Debian + VLESS

---

## Debian VPS (шлюз)

| Параметр | Значение |
|---|---|
| IP | `155.212.159.202` |
| Пользователь | `root` |
| Пароль | `xbYhfYS9T0nP` |
| SSH порт | `22` |
| Основной сетевой интерфейс | `eth0` |
| Шлюз провайдера | `155.212.159.201` |

---

## VLESS-сервер (выходной узел)

| Параметр | Значение |
|---|---|
| Домен | `sudvless.itfresh.ru` |
| IP | `202.148.54.236` |
| Порт | `443` |
| Протокол | `VLESS + TLS` |
| UUID | `e6b3c9b8-ae7f-4ba2-9b7b-42c209d3baa1` |
| Encryption | `none` |
| TLS fingerprint | `chrome` |
| ALPN | `h2, http/1.1` |

---

## OpenConnect (ocserv) — текущий VPN

> WireGuard был заменён на OpenConnect, т.к. провайдер блокировал UDP 51820.

### Сервер (Debian)

| Параметр | Значение |
|---|---|
| Порт | `443` (TCP + UDP) |
| Протокол | `Cisco AnyConnect / OpenConnect` |
| Конфиг | `/etc/ocserv/ocserv.conf` |
| TUN device | `vpns` (создаёт vpns0) |
| Подсеть клиентов | `192.168.8.0/24` |
| IP шлюза (Debian) | `192.168.8.1` |

### Клиент (Keenetic)

| Параметр | Значение |
|---|---|
| Сервер | `155.212.159.202` |
| Порт | `443` |
| Пользователь | `itfresh` |
| Пароль | `Itfresh2012` |
| Протокол | `Cisco AnyConnect / OpenConnect` |
| IP клиента | `192.168.8.80` (назначается сервером) |

---

## WireGuard (неактивен — заблокирован провайдером)

> Конфиги сохранены на сервере в `/etc/wireguard/wg0.conf`, но сервис остановлен и отключён.

| Параметр | Значение |
|---|---|
| Порт | `51820` (UDP — заблокирован провайдером) |
| IP шлюза | `10.8.0.1/24` |
| PublicKey сервера | `QgMaehDNQwB5UWYA8qxlhvbv0A9gqBxYQHzMbW5YCTg=` |
| PublicKey Keenetic | `MRpFXr3Vq30DrlBdW18pELdfTY+f6/USxjcMTsbM9kg=` |

---

## Сервисы на Debian

| Сервис | Адрес | Назначение |
|---|---|---|
| xray SOCKS5 | `127.0.0.1:10808` | Прямой тест VLESS с сервера |
| xray TPROXY | `0.0.0.0:12345` | Перехват трафика OpenConnect клиентов |
| ocserv | `0.0.0.0:443` | VPN-туннель с Keenetic (AnyConnect) |

---

## Сеть

| Параметр | Значение |
|---|---|
| OpenConnect подсеть | `192.168.8.0/24` |
| IP шлюза (Debian) | `192.168.8.1` |
| IP клиента Keenetic | `192.168.8.80` |
| iptables chain | `OCVPN` (перехват с vpns+) |
| fwmark routing | `ip rule fwmark 1 → table 100`, `table 100: local default dev lo` |

---

## Скрипты управления (Windows)

```
py -3 "C:/vless_new_setup.py"   — полная установка WireGuard + xray (если UDP 51820 открыт)
py -3 "C:/ocserv_setup.py"      — установка OpenConnect + xray TPROXY
py -3 "C:/ocserv_check.py"      — диагностика ocserv + xray + TPROXY счётчиков
py -3 "C:/vless_diag_fix.py"    — диагностика + пересоздание TPROXY правил
```
