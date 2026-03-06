# OpenClaw API Monitor

自动检测部署在 Linux 上的 [OpenClaw](https://docs.openclaw.ai/) 是否出现**大模型 API 调用失败**（如 API 限流、tokens 限制、配额等），并在发现失败后**持续监测**直至 API 恢复。

适合在 VPS/服务器上长期运行，配合 systemd 或 cron 使用。

## 如何部署到 GitHub

在 GitHub 新建空仓库后，在项目目录执行：

```bash
git init
git add .
git commit -m "Initial commit: OpenClaw API monitor"
git branch -M main
git remote add origin https://github.com/EndlessWaltz-Xi/openclaw-api-monitor.git
git push -u origin main
```

更详细说明（含创建仓库、SSH、Token）见 [DEPLOY.md](DEPLOY.md)。

## 可行性说明

- **原理**：本工具按间隔请求 OpenClaw 网关（默认 `http://127.0.0.1:18789`）。`check_mode: chat` 时请求官方文档中的 [Chat Completions](https://docs.openclaw.ai/platforms/linux) 接口 `/v1/chat/completions`，能真实触发上游大模型调用；通过 HTTP 状态码和响应体关键词判断是否限流/配额/错误，失败后缩短间隔轮询直到恢复。
- **前置条件**：若使用 `check_mode: chat`，需在 OpenClaw 中开启 HTTP Chat Completions（如配置项 `gateway.http.endpoints.chatCompletions.enabled: true`）。若未开启，可先用 `check_mode: ping` 只检测网关是否存活。
- **如何自测**：克隆后先安装依赖 `pip install -r requirements.txt`，再执行一次检查（成功退出 0，失败退出 1）：
  ```bash
  cp config.example.yaml config.yaml
  # 编辑 config.yaml 中 base_url、auth_token（若需要）
  python run.py --once
  echo "Exit code: $?"
  ```
  或用错误地址验证“失败”逻辑：把 `base_url` 改为 `http://127.0.0.1:19999` 时 `run.py --once` 应得到退出码 1。

## 功能

- **健康检查**：按配置间隔请求 OpenClaw 网关（`base_url`），可选「仅 ping」或「发送最小 chat 请求」以真实触发大模型调用。
- **失败判定**：  
  - HTTP 状态码在配置的 `failure_status_codes` 内（如 429、502、503）；或  
  - 响应体中包含配置的 `failure_keywords`（如 rate limit、quota、token、限流、配额等）。
- **恢复监测**：一旦判定为失败，自动缩短检查间隔，持续重试直到某次检查通过，再恢复为正常间隔并可选执行恢复回调。

## 环境要求

- Python 3.8+
- Linux（推荐与 OpenClaw 同机部署）

## 安装

```bash
git clone https://github.com/EndlessWaltz-Xi/openclaw-api-monitor.git
cd openclaw-api-monitor
pip install -r requirements.txt
```

无需 `pip install -e .` 也可运行：使用项目根目录的 `run.py`（见下方「运行」）。

## 配置

1. 复制示例配置并编辑：

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml，至少确认 base_url、check_mode、check_interval 等
```

2. 若 OpenClaw 网关启用了鉴权，在 `config.yaml` 中设置 `auth_token`（与 `gateway.auth.token` 一致）。

3. 主要选项说明：

| 选项 | 说明 |
|------|------|
| `base_url` | OpenClaw 网关地址，默认 `http://127.0.0.1:18789` |
| `auth_token` | 可选，网关 Bearer 鉴权 token |
| `check_mode` | `ping` 只请求根路径；`chat` 发送最小 `/v1/chat/completions` 请求（推荐） |
| `check_interval` | 正常时检查间隔（秒） |
| `recovery_interval` | 失败后恢复监测时的检查间隔（秒） |
| `failure_status_codes` | 视为失败的 HTTP 状态码列表 |
| `failure_keywords` | 响应体中出现即视为失败的关键词（可含中英文） |
| `on_failure_command` | 可选，首次判定失败时执行的 shell 命令 |
| `on_recovery_command` | 可选，恢复时执行的 shell 命令 |
| `log_level` / `log_output` | 日志级别与输出（stdout 或文件路径） |

## 运行

**推荐：克隆后直接运行（无需 pip install 本包）**

```bash
cp config.example.yaml config.yaml
# 按需编辑 config.yaml（base_url、auth_token 等）

python run.py          # 持续监测
python run.py --once   # 单次检查（成功退出 0，失败退出 1）
```

- 若已 `pip install -e .`，也可用：`python -m openclaw_monitor` 或 `openclaw-monitor`
- Linux 下可用：`./scripts/run.sh`

- 指定配置文件（Windows 用 set，Linux/macOS 用 export）：

```bash
# Linux / macOS
OPENCLAW_MONITOR_CONFIG=/path/to/config.yaml python run.py

# Windows PowerShell
$env:OPENCLAW_MONITOR_CONFIG="config.yaml"; python run.py
```

- 使用 systemd（用户服务示例）：

```bash
cp systemd/openclaw-api-monitor.service ~/.config/systemd/user/
# 编辑该文件，将 WorkingDirectory 与 OPENCLAW_MONITOR_CONFIG 改为你的项目路径，
# 将 ExecStart 改为实际可用的命令，例如：
#   ExecStart=/usr/bin/python3 -m openclaw_monitor
# 若已 pip install -e . 可改为： ExecStart=%h/.local/bin/openclaw-monitor
systemctl --user daemon-reload
systemctl --user enable --now openclaw-api-monitor.service
```

## 行为说明

1. **正常**：每次检查成功则等待 `check_interval` 秒后再次检查。  
2. **失败**：某次检查被判定为失败（状态码或关键词命中）时：
   - 记录失败并可选执行 `on_failure_command`；
   - 进入「恢复监测」：每隔 `recovery_interval` 秒重试一次。
3. **恢复**：某次检查成功则视为恢复，记录并可选执行 `on_recovery_command`，然后回到正常间隔。

## 开源协议

MIT License。详见 [LICENSE](LICENSE)。

## 贡献

欢迎提交 Issue 与 Pull Request。
