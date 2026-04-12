# Veeam FTP Server Setup - ITfreshFTP

**Server:** ITfreshFTP (37.228.92.57)
**OS:** Windows Server 2025 Standard (Build 26100)
**Setup date:** 2026-04-12
**Last updated:** 2026-04-13

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
- **Compression:** ZSTD, level 1
- **Schedule:** Daily at 02:00, duration 8 hours
- **CPU limit:** 50%
- **Min file age:** 0 hours (dedup even new files)
- **Volumes:** E:, F:, G:
- **Service:** `refsdedupsvc` (Running)
- **First full run:** started manually 2026-04-13
- **Status:** Active, processing ~1.4 TB of data

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
