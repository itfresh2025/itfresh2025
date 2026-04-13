# Veeam FTP Server Setup - ITfreshFTP

**Server:** ITfreshFTP (37.228.92.57)
**OS:** Windows Server 2025 Standard (Build 26100)
**Setup date:** 2026-04-12
**Last updated:** 2026-04-13 (audit + fixes)
**Password:** `Evgeniy@201028!!!` (user: администратор)

---

## Disks

| Drive | Label | FileSystem | Size TB | Used GB | Purpose |
|-------|-------|-----------|---------|---------|---------|
| C: | (system) | NTFS | 0.3 | - | System |
| E: | Dimax | ReFS 64KB | 10 | 129.94 | Dimax FTP |
| F: | Klient_FTP | ReFS 64KB | 30 | 746.15 | Client FTP |
| G: | ITfresh | ReFS 64KB | 40 | 509.67 | ITfresh FTP |

---

## ReFS Deduplication

- **Type:** DedupAndCompress (native WS2025 ReFS dedup)
- **Schedule:** Daily at 02:00, duration 8 hours
- **Service:** `refsdedupsvc` (Running, **StartType: Automatic** — исправлено 2026-04-13)
- **NTFS Dedup feature:** Installed, but не используется (Get-DedupVolume пустой — это нормально, работает ReFS dedup)
- **Назначение сервера:** FTP-хранилище для бэкап-копий клиентов. Veeam B&R не используется — клиенты заливают копии по FTP.
- **First full run:** started manually 2026-04-13

### Статус по томам (аудит 2026-04-13)

| Volume | Enabled | Compression | Compressed | Used | LastRun | Duration | NextRun |
|--------|---------|-------------|------------|------|---------|----------|---------|
| E: | True | **ZSTD** level 1 | 295.75 MiB | 861.73 GiB | 13.04.2026 02:00 | 7m 27s | 14.04.2026 02:00 |
| F: | True | **LZ4** level 1 | 135.09 GiB | 1.94 TiB | 13.04.2026 01:29 | 8h 16m | 14.04.2026 02:00 |
| G: | True | **LZ4** level 1 | 923.88 MiB | 510.23 GiB | 13.04.2026 01:29 | 52m | 14.04.2026 02:00 |

**Замечания:**
- E: использует ZSTD, F: и G: используют LZ4 — формат зашит в метаданные тома при первом включении, **сменить без пересоздания тома нельзя** (Enable-ReFSDedup не имеет параметра CompressionFormat)
- LZ4 быстрее при сжатии/разжатии, ZSTD лучше по ratio — для FTP-бэкапов оба варианта приемлемы
- Deduplication = 0 B на всех томах — файлы уникальные (бэкапы разных клиентов), это нормально
- Full dedup jobs запущены на всех томах 2026-04-13

### Dedup Commands

```powershell
# Check status
Get-ReFSDedupStatus -Volume E:

# Start manual job
Start-ReFSDedupJob -Volume E: -Full

# Stop job
Stop-ReFSDedupJob -Volume E:

# View/change schedule
Get-ReFSDedupSchedule -Volume E:
Set-ReFSDedupSchedule -Volume E: -Start "02:00" -Duration (New-TimeSpan -Hours 8) -Days Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday
```

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

Password format: `Primus@8283.ru` + first letter of username (uppercase)

| # | User | Password | Path | Status |
|---|------|----------|------|--------|
| 1 | Admink | Primus@8283.ruA | `E:\` | OK |
| 2 | ArtMaster | Primus@8283.ruA | `F:\FTP\ArtMaster` | OK |
| 3 | Baykon | Primus@8283.ruB | `F:\FTP\Baykon` | OK |
| 4 | Brain | Primus@8283.ruB | `F:\FTP\Brain` | OK |
| 5 | Dayv | Primus@8283.ruD | `F:\FTP\Dayv` | OK |
| 6 | Dimax | Primus@8283.ruD | `E:\FTP\Dimax` | OK |
| 7 | Dimax_obmen | Primus@8283.ruD | `E:\FTP\Dimax_Obmen` | OK |
| 8 | Esko | Primus@8283.ruE | `F:\FTP\Esko` | OK |
| 9 | ETS | Primus@8283.ruE | `F:\FTP\ETS` | OK |
| 10 | FU | Primus@8283.ruF | `F:\FTP\FU` | OK |
| 11 | Genesis | Primus@8283.ruG | `F:\FTP\Genesis` | OK |
| 12 | Genesis_arhiv | Primus@8283.ruG | `F:\FTP\Genesis\arhiv` | OK |
| 13 | isk | Primus@8283.ruI | `F:\FTP\ISK\Company` | OK |
| 14 | ITfresh | Primus@8283.ruI | `G:\FTP\ITfresh` | OK |
| 15 | Kloriant | Primus@8283.ruK | `F:\FTP\Kloriant` | OK |
| 16 | Lakom | Primus@8283.ruL | `F:\FTP\Lakom` | OK |
| 17 | nafko | Primus@8283.ruN | `F:\FTP\Nafko` | OK |
| 18 | Nils | Primus@8283.ruN | `F:\FTP\Nils` | OK |
| 19 | Optorika | Primus@8283.ruO | `F:\FTP\Optorika` | OK |
| 20 | Orbita | Primus@8283.ruO | `F:\FTP\Orbita` | OK |
| 21 | Polybit | Primus@8283.ruP | `F:\FTP\Polybit` | OK |
| 22 | Solis | Primus@8283.ruS | `F:\FTP\Solis` | OK |
| 23 | Ssys | Primus@8283.ruS | `F:\FTP\Ssys` | OK |
| 24 | SU87 | Primus@8283.ruS | `F:\FTP\SU87` | OK |
| 25 | sudex | Primus@8283.ruS | `F:\FTP\Sudex` | OK |
| 26 | Ticket | Primus@8283.ruT | `F:\FTP\ticket` | OK |
| 27 | Tornadologo | Primus@8283.ruT | `F:\FTP\Tornadologo` | OK |
| 28 | Velasat | Primus@8283.ruV | `F:\FTP\Velasat` | OK |
| 29 | Volvo | Primus@8283.ruV | `F:\FTP\volvo` | OK |

**All 29 users tested OK via FTP localhost (2026-04-12).**

---

## Subfolders

Each user folder contains:
- `SQL/` - for SQL backups
- `Company/` - for company data

Exceptions:
- `Genesis_arhiv` and `isk` - no subfolders (already specific paths)
- `E:\FTP\ITfresh` - created per user request (no subfolders)

---

## FTP Upload Stats (2026-04-13)

| User | Files | Size |
|------|-------|------|
| Baykon | 18,923 | 46.68 GB |
| Genesis | 12,441 | 51.76 GB |
| ISK | 1,675 | 4.31 GB |
| Dayv | 1 | ~0 MB |
| **Total** | **33,040** | **~102.75 GB** |

---

## Access

- **FTP:** `ftp://37.228.92.57`
- **RDP:** `37.228.92.57:3389` (enabled, user: администратор)
- **WAC:** Install `C:\WAC_Install.exe` via RDP for web management on port 443

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

---

## Audit 2026-04-13

### System Info

| Param | Value |
|-------|-------|
| Hostname | ITfreshFTP |
| OS | Windows Server 2025 Standard Build 26100 |
| Domain | WORKGROUP |
| CPU | Intel Xeon E5-2690 v2 @ 3.00GHz (40 vCPU) |
| RAM | 32 GB (23.6 GB free) |
| Uptime | ~13.5 hours |

### Key Findings

1. **Veeam B&R не используется** — сервер является FTP-хранилищем, клиенты заливают бэкап-копии по FTP
2. **FileZilla Server НЕ установлен** — FTP работает через **IIS FTP (ftpsvc)**
3. **ReFS дедупликация ВКЛЮЧЕНА** на всех 3 томах (E:, F:, G:) — E: = ZSTD, F:/G: = LZ4
4. **Дедупликация = 0 B** — файлы уникальные (бэкапы разных клиентов), работает только compression — это нормально
5. **NTFS Dedup feature** установлена, но не используется (ReFS dedup работает отдельно)

### Applied Fixes (2026-04-13)

- [x] `refsdedupsvc` переведён в **StartType=Automatic** (был Manual)
- [x] Расписание F: восстановлено (daily 02:00, 8h) — было сброшено при disable/enable
- [x] Запущены full dedup jobs на E:, F:, G:
- [ ] ~~Сменить LZ4 на ZSTD для F: и G:~~ — **невозможно** без пересоздания тома, формат зашит в метаданные ReFS
- [ ] Отмонтировать ISO на D: — VMware virtual CD-ROM, нужно отключить через ESXi

### Services Status

| Service | Status | StartType |
|---------|--------|-----------|
| ftpsvc (IIS FTP) | Running | Automatic |
| W3SVC (IIS Web) | Running | Automatic |
| refsdedupsvc (ReFS Dedup) | Running | **Automatic** (fixed) |

### Firewall (actual open ports)

21, 22, 80, 135, 443, 445, 990, 3389, 5985, 7250, 8172, 9955, 60000-65535 TCP + various UDP
