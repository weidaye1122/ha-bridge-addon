# HA Bridge Home Assistant Add-on

这是独立的 HA 插件安装仓库，消费已发布的 HA Bridge 镜像，不复制主程序源码。

- `repository.yaml`：插件仓库信息。
- `ha_bridge/config.yaml`：插件版本与配置；使用与安装见 [插件说明](ha_bridge/README.md) 和 [使用文档](ha_bridge/DOCS.md)。
- `release/`：发布与升级验证工具。
- `tests/test_release_flow.py`：发布流程检查。

规则见 [AGENTS.md](AGENTS.md)。在工作区可执行 `../ha-bridge/.venv/bin/python -m pytest tests/test_release_flow.py -q`；实际发布先检查 `release/publish_addon_release.sh` 参数，升级验证按 `release/verify_addon_upgrade.sh`。测试通过不代替真实 HAOS 升级验收。

## 仓库与开发规则

本目录是独立 Git 项目，开发规则见 [AGENTS.md](AGENTS.md)。源码、锁文件与规则由本仓库管理，数据、依赖和生成包按 `.gitignore` 留在本机。总工作区的项目清单与公共规则单独管理，目录整理不代表业务功能已发布。

开发定位、环境、验证与交付边界见 [开发入口](docs/DEVELOPMENT.md)。
