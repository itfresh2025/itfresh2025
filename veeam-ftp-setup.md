# Veeam FTP Server Setup - ITfreshFTP

**Server:** ITfreshFTP (37.228.92.57)
**OS:** Windows Server 2025 Standard (Build 26100)
**Date:** 2026-04-12

---

## Disks

| Drive | Label | FileSystem | Size TB | Purpose |
|-------|-------|-----------|---------|---------|
| C: | (system) | NTFS | 0.3 | System |
| E: | Dimax | ReFS 64KB | 10 | Dimax FTP |
| F: | Klient_FTP | ReFS 64KB | 30 | Client FTP |
| G: | ITfresh | ReFS 64KB | 40 | ITfresh FTP |

---

## Deduplication

- **Type:** ReFS DedupAndCompress (native WS2025)
- **Schedule:** Daily at 02:00, 6 hours duration
- **Volumes:** E:, F:, G:

---

## FTP Server (IIS)

- **Site:** FTP_Clients
- **Port:** 21
- **Passive ports:** 60000-65535
- **Auth:** Basic (anonymous disabled)
- **SSL:** Allow (not required)
- **User Isolation:** Enabled (mode 3 - LocalUser virtual directories)

---

## FTP Users and Paths

| # | User | Path | Status |
|---|------|------|--------|
| 1 | Admink | `E:\` | OK |
| 2 | ArtMaster | `F:\FTP\ArtMaster` | OK |
| 3 | Baykon | `F:\FTP\Baykon` | OK |
| 4 | Brain | `F:\FTP\Brain` | OK |
| 5 | Dayv | `F:\FTP\Dayv` | OK |
| 6 | Dimax | `E:\FTP\Dimax` | OK |
| 7 | Dimax_obmen | `E:\FTP\Dimax_Obmen` | OK |
| 8 | Esko | `F:\FTP\Esko` | OK |
| 9 | ETS | `F:\FTP\ETS` | OK |
| 10 | FU | `F:\FTP\FU` | OK |
| 11 | Genesis | `F:\FTP\Genesis` | OK |
| 12 | Genesis_arhiv | `F:\FTP\Genesis\arhiv` | OK |
| 13 | isk | `F:\FTP\ISK\Company` | OK |
| 14 | ITfresh | `G:\FTP\ITfresh` | OK |
| 15 | Kloriant | `F:\FTP\Kloriant` | OK |
| 16 | Lakom | `F:\FTP\Lakom` | OK |
| 17 | nafko | `F:\FTP\Nafko` | OK |
| 18 | Nils | `F:\FTP\Nils` | OK |
| 19 | Optorika | `F:\FTP\Optorika` | OK |
| 20 | Orbita | `F:\FTP\Orbita` | OK |
| 21 | Polybit | `F:\FTP\Polybit` | OK |
| 22 | Solis | `F:\FTP\Solis` | OK |
| 23 | Ssys | `F:\FTP\Ssys` | OK |
| 24 | SU87 | `F:\FTP\SU87` | OK |
| 25 | sudex | `F:\FTP\Sudex` | OK |
| 26 | Ticket | `F:\FTP\ticket` | OK |
| 27 | Tornadologo | `F:\FTP\Tornadologo` | OK |
| 28 | Velasat | `F:\FTP\Velasat` | OK |
| 29 | Volvo | `F:\FTP\volvo` | OK |

**All 29 users tested OK via FTP localhost.**

---

## Subfolders

Each user folder contains:
- `SQL/` - for SQL backups
- `Company/` - for company data

Exceptions:
- `Genesis_arhiv` and `isk` - no subfolders (already specific paths)
- `E:\FTP\ITfresh` - created per user request (no subfolders)

---

## Access

- **FTP:** `ftp://37.228.92.57`
- **RDP:** `37.228.92.57:3389` (enabled)
- **Web Management:** `https://37.228.92.57:8172` (IIS Manager)
- **Passwords:** `C:\FTP_Users_Passwords.txt` on server

---

## Firewall Rules

| Rule | Port | Protocol |
|------|------|----------|
| FTP Control | 21 | TCP |
| FTP Passive | 60000-65535 | TCP |
| RDP | 3389 | TCP |
| HTTP | 80 | TCP |
| HTTPS | 443 | TCP |
| IIS Web Mgmt | 8172 | TCP |

---

## Monitoring

Desktop shortcut "FTP Monitor" on administrator desktop runs `C:\FTP_Monitor.ps1`:
- Shows FTP site state
- Active sessions
- Current connections (netstat :21)
- Recent FTP log entries
- Auto-refreshes every 5 seconds
