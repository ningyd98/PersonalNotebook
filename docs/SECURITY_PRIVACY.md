# Security & Privacy

## 核心原则

PersonalNotebook 坚持**本地优先**原则：
- Core 服务运行在用户自己的设备上
- 文档数据存储在本机 PostgreSQL / MinIO / Qdrant
- 不向任何外部服务上传文档内容、chunk、向量

## Paired Token 机制

| 机制 | 说明 |
|------|------|
| Token 生成 | `POST /auth/pair/create` → 返回明文 token **仅此一次** |
| Token 存储 | 数据库只存 `sha256(token)`，明文 token 不可逆 |
| Token 过期 | 默认 24 小时 |
| Token 撤销 | `DELETE /auth/devices/{id}` → 立即生效 (仅 localhost) |
| 业务鉴权 | `Authorization: Bearer <token>` → sha256 比对 PairedDevice |
| 401 响应 | revoked / expired / invalid token 均返回 401 |

## 数据存储位置

| 组件 | 存储位置 |
|------|---------|
| PostgreSQL | Docker volume `infra/data/postgres/` |
| Qdrant | Docker volume `infra/data/qdrant/` |
| MinIO | Docker volume `infra/data/minio/` |
| Redis | 内存 (无持久化) |

## 移动端安全

| 项目 | 方式 |
|------|------|
| Token 存储 | `flutter_secure_storage` (iOS Keychain / Android EncryptedSharedPreferences) |
| Core URL | `flutter_secure_storage` |
| deviceId | `flutter_secure_storage` |
| 断连清除 | unpair → 删除所有 secure storage 条目 |

## 日志脱敏

| 区域 | 措施 |
|------|------|
| Backend `/api/system/logs` | `_sanitize()` 正则脱敏 SECRET_KEY/PASSWORD/TOKEN/API_KEY |
| Flutter DiagnosticsService | 不记录 token、不记录完整 deviceId (仅前 8 位) |
| ApiClient | 不记录完整请求 body; 错误摘要不含 Bearer |

## 不应上传的文件

- `upload-keystore.jks`
- `key.properties`
- `.env` (含真实密钥)
- 任何 `.apk` / `.ipa` / `.app` / `.exe` / `.dmg` / `.msix`
- `flutter_secure_storage` 导出的数据

## 内测反馈安全

反馈内容**不应包含**：
- Token 明文
- deviceId 完整值
- 用户文档内容
- Core 部署环境的密码/密钥
- 个人身份信息

## 发现泄漏后的处理

1. 立即 `DELETE /auth/devices/{id}` 撤销泄露的 token
2. 如 `.env` 密钥泄露，旋转所有密钥
3. 如 keystore 泄露，重新生成并在 Google Play 中使用新签名密钥
4. 通知所有内测用户重新配对
