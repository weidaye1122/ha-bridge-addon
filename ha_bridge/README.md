# HA Bridge

HA Bridge 的 Home Assistant Add-on 封装。

安装后启动 Add-on，在浏览器打开：

```text
http://Home Assistant_IP:18080
```

- [官网](https://wiki.habridge.cn/)
- [使用说明](https://wiki.habridge.cn/manual/first-setup.html)

Add-on 使用 Supervisor 管理的 `/data` 保存数据库、项目、素材、授权状态、Home Assistant 链接及 HA Bridge 本地账号；`/run/secrets` 保存相关的本地安全信息。升级和重启后这些数据会继续保留。
