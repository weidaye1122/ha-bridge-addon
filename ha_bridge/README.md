# HA Bridge

HA Bridge 的 Home Assistant Add-on 封装。

安装后启动 Add-on，在浏览器打开：

```text
http://Home Assistant_IP:18080
```

Add-on 使用 Supervisor 管理的 `/data` 保存数据库、项目、素材、授权状态和其他应用数据；加密密钥通过 Supervisor 管理的 Add-on 配置目录挂载到容器 `/run/secrets`，升级和重启不会丢失。

本 Add-on 复用已经发布的 HA Bridge 镜像，不在本仓库保存 HA Bridge 主项目源码。
