# HA Bridge

HA Bridge 的 Home Assistant Add-on 封装。

安装后启动 Add-on，在浏览器打开：

```text
http://Home Assistant_IP:18080
```

Add-on 使用 Supervisor 管理的 `/data` 保存数据库、项目、素材、授权状态和其他应用数据；加密密钥通过 Supervisor 管理的 Add-on 配置目录挂载到容器 `/run/secrets`，升级和重启不会丢失。

本 Add-on 使用基于 HA Bridge 正式镜像的极薄适配镜像。适配层只负责初始化 Supervisor 挂载目录，随后仍降权为 `ha-bridge` 用户运行。本仓库不保存 HA Bridge 主项目源码。
