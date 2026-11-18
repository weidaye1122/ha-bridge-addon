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


## HTTPS 反向代理与非默认端口

HTTP 请求带同源标记时，主程序可自动兼容 Nginx Proxy Manager 等反代的 HTTPS 终止、Host 改写或外部端口省略，配对与实时/视频连接使用同一套来源规则。

浏览器缺少该标记、仍无法配对或实时连接时（部分现代浏览器的 WebSocket 也不携带该标记），在本应用“配置”的“额外公开访问来源”中填写完整来源，保存后重启应用，例如：

```yaml
additional_public_origins:
  - "https://panel.example.com:8443"
```

只填写协议、域名和实际端口，不带 `/login`、`/habridge/...` 等路径，不填写通配符。默认空列表保持原行为，新增来源保留局域网直连；登录、配对码、项目及授权限制继续生效。此选项由匹配的新主镜像读取，旧主镜像不会因配置变化获得兼容能力。显式设置过 `APP_BASE_URL` 的部署仍遵循原固定来源限制。
