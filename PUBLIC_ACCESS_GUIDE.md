# AI热点监控工具 - 公网访问配置指南

## 当前网络配置状态

✅ **已完成配置修改**：
- `config.yaml` 中 host 已从 `127.0.0.1` 修改为 `0.0.0.0`
- `.env` 文件中已设置 `HOST=0.0.0.0`
- 服务已支持局域网内其他设备访问

## 测试验证结果

| 访问方式 | 状态 | 地址示例 |
|---------|------|---------|
| 本地访问 | ✅ 通过 | http://localhost:8000 |
| 局域网访问 | ✅ 通过 | http://192.168.31.21:8000 |
| 公网访问 | ⚠️ 需额外配置 | 见下方方案 |

## 公网访问方案

### 方案一：内网穿透（推荐，最简单）

使用内网穿透工具，无需公网IP和服务器：

#### 1. ngrok（免费，适合临时使用）
```bash
# 安装 ngrok
brew install ngrok

# 注册并获取 authtoken: https://dashboard.ngrok.com
ngrok config add-authtoken YOUR_AUTHTOKEN

# 启动穿透（将本地8000端口暴露到公网）
ngrok http 8000
```

#### 2. frp（自建，长期稳定）
需要有公网服务器部署 frps，本地运行 frpc。

frpc.ini 配置示例：
```ini
[common]
server_addr = your-server-ip
server_port = 7000
token = your-token

[ai-hot-monitor]
type = http
local_port = 8000
custom_domains = ai-hot.your-domain.com
```

### 方案二：云服务器部署（推荐，生产环境）

将项目部署到云服务器（阿里云、腾讯云、AWS等）：

```bash
# 1. 使用 Docker 部署（推荐）
docker-compose up -d

# 2. 或使用 systemd 服务
sudo systemctl enable ai-hot-monitor
sudo systemctl start ai-hot-monitor
```

#### Nginx 反向代理配置
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # 强制 HTTPS（推荐）
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 方案三：DDNS + 端口映射（有公网IP时）

如果您有公网IP：

1. **路由器端口映射**：将外网端口映射到内网 `192.168.31.21:8000`
2. **配置 DDNS**：使用花生壳、no-ip 等解决动态IP问题
3. **防火墙设置**：
   ```bash
   # Linux (ufw)
   sudo ufw allow 8000/tcp
   
   # macOS
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/python3
   ```

## 安全配置建议

### 1. 启用身份验证
项目已内置登录功能，首次访问需要登录。

### 2. 使用 HTTPS（强烈推荐）
使用 Let's Encrypt 免费证书：
```bash
# 安装 certbot
brew install certbot

# 获取证书
certbot certonly --standalone -d your-domain.com
```

### 3. 限制访问IP（可选）
修改 `config.yaml` 限制特定IP：
```yaml
app:
  host: 192.168.31.21  # 仅监听特定IP
```

### 4. 使用 VPN（最安全）
建议通过 WireGuard、OpenVPN 等 VPN 访问，不直接暴露服务。

## 快速启动命令

```bash
# 1. 本地开发模式（仅本地访问）
HOST=127.0.0.1 python3 main.py

# 2. 局域网共享模式（推荐日常使用）
./start.sh

# 3. Docker 部署（生产环境）
docker-compose up -d
```

## 防火墙配置参考

### macOS
```bash
# 查看防火墙状态
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# 允许特定端口（需要关闭 SIP 或使用第三方工具如 pfctl）
echo "rdr pass inet proto tcp from any to any port 8000 -> 127.0.0.1 port 8000" | sudo pfctl -ef -
```

### Linux (ufw)
```bash
sudo ufw allow 8000/tcp
sudo ufw reload
```

### Windows
```powershell
# PowerShell 管理员
New-NetFirewallRule -DisplayName "AI Hot Monitor" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

## 故障排查

### 无法从局域网访问？
1. 检查防火墙设置
2. 确认 `config.yaml` 中 `host: 0.0.0.0`
3. 检查网络是否在同一网段

### 启动报错？
1. 检查端口是否被占用：`lsof -i :8000`
2. 查看日志：`tail -f logs/app.log`
3. 检查依赖是否完整：`pip install -r requirements.txt`

## 总结

- ✅ 本地访问：`http://localhost:8000`
- ✅ 局域网访问：`http://<本机IP>:8000`
- ⚠️ 公网访问：建议通过内网穿透或云服务器部署
- 🔒 安全提醒：公网访问务必启用 HTTPS 和身份验证
