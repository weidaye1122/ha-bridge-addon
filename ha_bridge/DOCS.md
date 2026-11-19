# HA Bridge 使用说明

## 启动与首次设置

1. 点击「启动」。状态显示「运行中」后，点击「打开网页界面」。
2. 创建 HA Bridge 的本地管理员账号，输入激活码完成激活。
3. 在 HA Bridge 中填写 Home Assistant 的服务地址和长期访问令牌。测试连接成功后保存。

同一局域网内也可直接用浏览器打开，例如 `http://192.168.1.10:18080`。请把示例 IP 换成你的 Home Assistant 主机局域网地址。

[首次设置与激活](https://wiki.habridge.cn/manual/first-setup.html) · [连接 Home Assistant](https://wiki.habridge.cn/manual/connect-home-assistant.html)

## 更新

更新前可在 Home Assistant 创建包含 HA Bridge 的备份。在原来的 HA Bridge 应用页面点击「更新」，保留现有应用数据。更新完成后，打开网页界面检查原有仪表盘和 Home Assistant 连接。

## 备份与迁移

- **完整恢复 HA Bridge Add-on**。使用 Home Assistant 备份，确认备份和恢复时都包含 HA Bridge 应用及其数据。需要回退时，使用升级前与旧版本匹配的完整备份。
- **从 Docker 迁移仪表盘、户型和 HA 连接**。在原安装的 HA Bridge 中导出加密的 `.habackup` 文件。新安装完成账号设置和激活后，再导入备份。导入会替换目标安装的业务数据，目标安装的管理员账号和授权继续使用，中控设备需要重新配对。

操作步骤见 [备份与恢复](https://wiki.habridge.cn/maintenance/backup-restore.html)。

公开反馈问题时，请提供 Add-on 版本、安装来源和脱敏后的日志。备份文件、令牌、激活码、密码和密钥请妥善保管。

## HTTPS 反向代理与非默认端口

HTTP 请求带同源标记时，主程序可自动兼容 Nginx Proxy Manager 等反代的 HTTPS 终止、Host 改写或外部端口省略，配对与实时/视频连接使用同一套来源规则。

浏览器缺少该标记、仍无法配对或实时连接时（部分现代浏览器的 WebSocket 也不携带该标记），在本应用“配置”的“额外公开访问来源”中填写完整来源，保存后重启应用，例如：

```yaml
additional_public_origins:
  - "https://panel.example.com:8443"
```

只填写协议、域名和实际端口，不带 `/login`、`/habridge/...` 等路径，不填写通配符。默认空列表保持原行为，新增来源保留局域网直连；登录、配对码、项目及授权限制继续生效。此选项由匹配的新主镜像读取，旧主镜像不会因配置变化获得兼容能力。显式设置过 `APP_BASE_URL` 的部署仍遵循原固定来源限制。
