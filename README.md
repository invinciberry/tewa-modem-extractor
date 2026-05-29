# TEWA Modem Telecomadmin Extractor · 天翼宽带光猫密码提取工具

[English](#english) · [中文](#中文)

---

## English

Automates extraction of the `telecomadmin` password from TEWA modems issued by China Telecom (天翼宽带).

### What it does

China Telecom TEWA modems have a hidden `telecomadmin` superuser account that is not accessible from the standard web UI. This tool automates the full extraction sequence:

1. Logs into the modem web UI to obtain a session key
2. Enables telnet via the `telandftpcfg.cmd` endpoint
3. Connects via telnet as `admin`
4. Derives candidate `su` passwords from the modem's MAC address and tries each one
5. Runs `telecomadmin get` to print the password

### Requirements

- Python 3.6+
- Local network access to the modem (same LAN)
- The web UI login credentials (the standard user account, e.g. `useradmin`)

### Usage

```bash
python3 modem_extract.py AA:BB:CC:DD:EE:FF
```

You will be prompted for the modem IP (default `192.168.1.1`) and web UI password if not supplied as flags.

#### All options

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

#### Example

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

### `generate_a1.py` — standalone password generator

`generate_a1.py` derives the `su` password candidates from a MAC address without connecting to the modem. Useful for testing or scripting.

```bash
python3 generate_a1.py AA:BB:CC:DD:EE:FF
```

### Notes

- Only works on TEWA modems (model numbers such as HG261, HG6143, and similar) issued by China Telecom.
- Requires physical or network access to your own modem. Do not use against devices you do not own or have permission to access.
- The `generate_a1` algorithm is embedded directly in `modem_extract.py`, so you only need that one file to run the full extraction.

---

## 中文

自动提取中国电信 TEWA 光猫的 `telecomadmin` 超级管理员密码。

### 功能说明

中国电信下发的 TEWA 光猫存在一个隐藏的 `telecomadmin` 超级管理员账号，在普通 Web 界面中无法直接访问。本工具自动执行以下完整提取流程：

1. 登录光猫 Web 管理界面，获取 session key
2. 通过 `telandftpcfg.cmd` 接口开启 Telnet 功能
3. 以 `admin` 账号通过 Telnet 登入
4. 根据光猫 MAC 地址推算 `su` 密码候选值并逐一尝试
5. 执行 `telecomadmin get` 获取超级管理员密码

### 环境要求

- Python 3.6 及以上
- 与光猫处于同一局域网（本地网络访问）
- 普通用户的 Web 管理界面账号密码（如 `useradmin`）

### 使用方法

```bash
python3 modem_extract.py AA:BB:CC:DD:EE:FF
```

若未通过参数指定，程序会交互式提示输入光猫 IP 地址（默认 `192.168.1.1`）和 Web 界面密码。

#### 完整参数说明

```
python3 modem_extract.py [--host IP] [--port PORT] [--web-user 用户名] [--web-pass 密码] [MAC地址]

位置参数：
  MAC地址             光猫 MAC 地址（支持多种格式：AA:BB:CC、AABBCCDDEEEE 等）

可选参数：
  --host IP          光猫 IP 地址（默认：192.168.1.1）
  --port PORT        Web 管理界面端口（默认：8080）
  --web-user 用户名   Web 管理界面用户名（默认：useradmin）
  --web-pass 密码     Web 管理界面密码
```

#### 示例

```
$ python3 modem_extract.py --host 192.168.1.1 --web-user useradmin AC:12:34:56:78:9A
Web UI password: ••••••••
[*] SU 候选密码: ['abcXYZ12', ...]
[*] 正在登录并开启 Telnet，目标：192.168.1.1:8080...
[*] 登录成功（sessionKey: 1234567890）
[*] Telnet 账号：admin / admin
[*] 正在连接 192.168.1.1:23...
  尝试 SU 密码：abcXYZ12
  [+] SU 提权成功
[+] telecomadmin 密码：ChinaNet@12345
```

### `generate_a1.py` — 独立密码推算工具

`generate_a1.py` 可在不连接光猫的情况下，单独根据 MAC 地址推算 `su` 候选密码，适用于测试或二次开发。

```bash
python3 generate_a1.py AA:BB:CC:DD:EE:FF
```

### 注意事项

- 本工具仅适用于中国电信下发的 TEWA 品牌光猫（如 HG261、HG6143 等型号）。
- 需要对目标设备具备合法访问权限，请勿在未经授权的设备上使用。
- `generate_a1` 算法已内嵌于 `modem_extract.py` 中，单独使用该文件即可完成完整提取，无需依赖 `generate_a1.py`。
