# App Troubleshooting (Phase 2C)

## 连接不上 Core

**问题**: App 启动后显示"无法连接 Core"或超时。

**检查**:
1. Core 服务是否运行: `curl http://localhost:8000/health`
2. 移动端不能用 `localhost`，需要用局域网 IP: `http://192.168.x.x:8000`
3. 确认 Core 监听 0.0.0.0 而非 127.0.0.1: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
4. 检查防火墙是否放行 8000 端口

## 401 Unauthorized

**问题**: API 调用返回 401。

**情况 1: Token 未提供**
- App 必须在 pairing 页输入/扫码获取 token
- 所有业务 API 需要 `Authorization: Bearer <token>` header

**情况 2: Token 过期或撤销**
- 回到 Pairing 页面重新配对
- desktop: `DELETE /auth/devices/{device_id}` 撤销后可重新创建

**情况 3: REQUIRE_PAIR_AUTH=false 关闭了鉴权**
- 开发环境可设置 `REQUIRE_PAIR_AUTH=false` 绕过
- 生产环境必须保持开启

## 403 Forbidden

**问题**: `/system/runtime/*` 返回 403。

**原因**: System Runtime API 仅允许 localhost 访问。移动端不应调用此 API。
**解决**: 移动端隐藏 Runtime Manager 入口。

## Docker 未启动

**问题**: Desktop Runtime Manager 报 Docker 错误。

**检查**:
1. Docker Desktop 是否安装并运行
2. `docker --version` 是否有输出
3. `docker compose version` 是否可用
4. `infra/docker-compose.yml` 是否存在

## 手机无法访问电脑 localhost

**问题**: 手机输入 `http://localhost:8000` 连接失败。

**解决**:
1. 电脑和手机必须在同一 Wi-Fi / 局域网
2. 获取电脑局域网 IP: `ifconfig | grep "inet "` (macOS/Linux) 或 `ipconfig` (Windows)，找 `192.168.x.x`
3. 手机使用 `http://192.168.x.x:8000`
4. 确保 Core 绑定 0.0.0.0: `--host 0.0.0.0`

## Android 局域网访问

**问题**: Android 无法访问 HTTP 地址。

**解决**:
- AndroidManifest.xml 添加: `android:usesCleartextTraffic="true"`
- Android 9+ 默认禁止 HTTP，需显式允许

## iOS 局域网权限

**问题**: iOS 无法访问局域网。

**解决**:
- Info.plist 添加 `NSLocalNetworkUsageDescription` 和 `NSBonjourServices`
- 首次访问时 iOS 会弹出权限请求，用户需允许

## 扫码失败

**问题**: QR 扫码不工作或 fallback 到手动输入。

**解决**:
1. 确认 CAMERA 权限已授予 (Android/iOS)
2. QR 码内容应为 JSON: `{"type":"personal_notebook_pairing","core_base_url":"...","token":"...","tenant_id":"default","expires_at":"..."}`
3. 如扫码不可用，使用手动输入 URL + Token

## Token 过期/撤销

**问题**: 之前配对的 App 突然无法使用。

**解决**:
1. App 检测到 401 → 跳转 PairingScreen
2. 清除本地 secure storage: Settings → 断开连接
3. 桌面端重新 `POST /auth/pair/create` 生成新 token
4. 重新扫码配对
