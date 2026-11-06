# HA Bridge Home Assistant Add-on

开发定位与修改影响见 [代码地图](docs/code-map/README.md)。

这是独立的 HA 插件安装仓库，通过不可变摘要消费 HA Bridge 镜像，不复制主程序源码；候选先验收，正式渠道随主程序统一提升。

- `repository.yaml`：插件仓库信息。
- `ha_bridge/config.yaml`：插件版本与配置；使用与安装见 [插件说明](ha_bridge/README.md) 和 [使用文档](ha_bridge/DOCS.md)。
- `release/`：发布与升级验证工具。
- `tests/test_release_flow.py`：发布流程检查。

规则见 [AGENTS.md](AGENTS.md)。日常执行 `sh tools/check.sh`，无需借用主程序环境。Add-on 始终跟随主程序，由主程序 `release/publish_full_release.sh` 统一发布；本仓库发布脚本承担其中的适配镜像和升级步骤。测试通过不代替真实 HAOS 升级验收。

## 仓库与开发规则

本目录是独立 Git 项目，开发规则见 [AGENTS.md](AGENTS.md)。源码、锁文件与规则由本仓库管理，数据、依赖和生成包按 `.gitignore` 留在本机。总工作区的项目清单与公共规则单独管理，目录整理不代表业务功能已发布。

开发定位、环境、验证与交付边界见 [开发入口](docs/DEVELOPMENT.md)。
