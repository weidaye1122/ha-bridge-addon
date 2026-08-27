# HA Bridge

HA Bridge 的 Home Assistant Add-on 封装。

安装后启动 Add-on，在浏览器打开：

```text
http://Home Assistant_IP:18080
```

Add-on 使用 Supervisor 管理的 `/data` 保存数据库、项目、素材、授权状态和其他应用数据；加密密钥通过 Supervisor 管理的 Add-on 配置目录挂载到容器 `/run/secrets`，升级和重启不会丢失。

本 Add-on 使用基于 HA Bridge 正式镜像的极薄适配镜像。适配层只负责初始化 Supervisor 挂载目录，随后仍降权为 `ha-bridge` 用户运行。本仓库不保存 HA Bridge 主项目源码。

## 正式发布

Add-on 正式镜像不是主镜像的简单标签，而是使用 `release/Dockerfile`
基于已经发布并锁定摘要的 HA Bridge 正式镜像重新构建。适配层只调整
Supervisor 挂载目录初始化所需的启动用户，不复制应用源码。

完整 HA Bridge 发布由主项目的 `release/publish_full_release.sh` 统一调用。
单独修复 Add-on 时，也可以显式提供主程序版本和适配修订号：

```bash
BASE_VERSION=0.4.2 ADDON_REVISION=2 ./release/publish_addon_release.sh publish
```
