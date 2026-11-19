# HA Bridge Home Assistant Add-on

HA Bridge 是一个智能家居可视化面板编辑器。你可以制作仪表盘和 3D 户型，在面板中查看设备状态并控制 Home Assistant 设备。

## 安装

适用于带应用商店的 Home Assistant，支持 AMD64 和 ARM64。

1. 在 Home Assistant 打开「设置 → 应用 → 安装应用」，从右上角菜单进入「仓库」。旧版界面中，「应用」可能显示为「Add-ons」。
2. 首次安装选择一个地址添加。国内网络优先选 Gitee，访问不畅时可选 GitHub。
   - Gitee 国内同步源 `https://gitee.com/weidaye1122/ha-bridge-addon`
   - GitHub 发布源 `https://github.com/weidaye1122/ha-bridge-addon`
3. 返回应用商店，搜索并安装「HA Bridge」。安装完成后点击「启动」，再点击「打开网页界面」。

详细步骤见 [HAOS 安装教程](https://wiki.habridge.cn/deploy/haos-addon.html)。

## 更新

已安装的用户请在原来的 HA Bridge 应用页面更新。从另一个仓库安装会创建独立实例，原有数据仍在原来的安装中。

新版本先发布到 GitHub，Gitee 随后自动同步。两个来源使用同一个阿里云容器镜像。暂时看不到新版本时，可以在应用商店执行「检查更新」。

[首次设置与激活](https://wiki.habridge.cn/manual/first-setup.html) · [备份与恢复](https://wiki.habridge.cn/maintenance/backup-restore.html)
