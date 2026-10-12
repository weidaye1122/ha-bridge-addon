# Add-on 开发入口

核对：2026-10-12，基线 `0a630a8`。这是主程序的安装适配层，消费正式镜像。

## 定位与边界

- [规则](../AGENTS.md)、[安装说明](../ha_bridge/README.md)、[使用文档](../ha_bridge/DOCS.md)。
- `repository.yaml`：HA 插件仓库；`ha_bridge/config.yaml`：版本、架构、镜像、环境与持久挂载；`ha_bridge/CHANGELOG.md`：插件日志。
- `release/Dockerfile`：已发布主镜像的适配；`release/version.py`：同步插件版本及日志；不在此复制业务代码。

## 验证

发布流程测试使用 Python 标准库，单独克隆也可在本仓库运行，无需安装主程序：

```sh
python3 -m unittest discover -s tests -p test_release_flow.py
sh -n release/publish_addon_release.sh
sh -n release/verify_addon_upgrade.sh
git diff --check
```

已有工作区也可用同级主程序 Python 环境运行 pytest。涉及镜像、目录初始化或挂载时，再按升级脚本验证隔离容器；脚本自建临时数据和容器，只清理自己的资源。

## 版本与交付

`主程序版本-插件修订号` 由 `release/version.py` 维护。改适配层检查 amd64/aarch64、持久 `data`/`secrets`、运行 UID 与更新渠道，不擅自清空用户安装数据。

正式入口 `release/publish_addon_release.sh preflight|publish`，阅读脚本后指定 `BASE_VERSION` / `ADDON_REVISION`；preflight 会查询远端 Git 和镜像，不是离线检查。实际 publish 会上传镜像、验证升级、更新版本并推送仓库，只有发布任务才执行。

`release/verify_addon_upgrade.sh` 的隔离 Docker 升级不能代替真实 Supervisor/HAOS 安装、Ingress 与用户升级验收。历史结果留在本机证据，插件最终日志维护于 CHANGELOG；没有接入三个项目的自动开发记录门禁，也未配置业务测试 CI。
