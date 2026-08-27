# 使用说明

## 首次安装

1. 在 Home Assistant 的 Add-on 商店安装并启动 HA Bridge。
2. 打开 `http://Home Assistant_IP:18080`。
3. 首次访问时设置管理员账号和密码。
4. 输入授权信息。
5. 在 HA Bridge 中配置 Home Assistant 地址和长期 Token。

## 升级

升级 Add-on 时不要删除 Add-on 数据。Supervisor 会保留 `/data` 和 `/run/secrets` 对应的持久化目录。

## 迁移现有 Docker 安装

如果从普通 Docker 迁移，请在迁移前备份 `/data` 和 `/run/secrets`。数据库与三个加密密钥必须一起保留：

```text
ha_credentials.key
display_pairing_codes.key
license_credentials.key
```
