# TEWA Modem Telecomadmin Extractor

Automates extraction of the `telecomadmin` password from TEWA modems issued by China Telecom (天翼宽带).

## What it does

China Telecom TEWA modems have a hidden `telecomadmin` superuser account that is not accessible from the standard web UI. This tool automates the full extraction sequence:

1. Logs into the modem web UI to obtain a session key
2. Enables telnet via the `telandftpcfg.cmd` endpoint
3. Connects via telnet as `admin`
4. Derives candidate `su` passwords from the modem's MAC address and tries each one
5. Runs `telecomadmin get` to print the password

## Requirements

- Python 3.6+
- Local network access to the modem (same LAN)
- The web UI login credentials (the standard user account, e.g. `useradmin`)

## Usage

```bash
python3 modem_extract.py AA:BB:CC:DD:EE:FF
```

You will be prompted for the modem IP (default `192.168.1.1`) and web UI password if not supplied as flags.

### All options

```
python3 modem_extract.py [--host IP] [--port PORT] [--web-user USER] [--web-pass PASS] [MAC]

positional arguments:
  MAC               Modem MAC address (any format: AA:BB:CC, AABBCCDDEE, etc.)

optional arguments:
  --host IP         Modem IP address (default: 192.168.1.1)
  --port PORT       Web UI port (default: 8080)
  --web-user USER   Web UI username (default: useradmin)
  --web-pass PASS   Web UI password
```

### Example

```
$ python3 modem_extract.py --host 192.168.1.1 --web-user useradmin AC:12:34:56:78:9A
Web UI password: ••••••••
[*] SU candidates: ['abcXYZ12', ...]
[*] Logging in and enabling telnet on 192.168.1.1:8080...
[*] Logged in (sessionKey: 1234567890)
[*] Telnet credentials: admin / admin
[*] Connecting to 192.168.1.1:23 via telnet...
  trying SU password: abcXYZ12
  [+] SU succeeded
[+] telecomadmin password: ChinaNet@12345
```

## `generate_a1.py` — standalone password generator

`generate_a1.py` derives the `su` password candidates from a MAC address without connecting to the modem. Useful for testing or scripting.

```bash
python3 generate_a1.py AA:BB:CC:DD:EE:FF
```

## Notes

- Only works on TEWA modems (model numbers such as HG261, HG6143, and similar) issued by China Telecom.
- Requires physical or network access to your own modem. Do not use against devices you do not own or have permission to access.
- The `generate_a1` algorithm is embedded directly in `modem_extract.py`, so you only need that one file to run the full extraction.
