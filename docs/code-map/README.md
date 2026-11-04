# Add-on 代码地图

2026-11-04 局部核对：基线 `3a1e06d`（原0.8.4-1及规则差异）加分组开发说明。Add-on继续随主程序完整发布，主程序通过项目登记/显式路径调用本仓库脚本，原发布顺序、版本、digest与挂载实现未改。[tools/check.sh](../../tools/check.sh) 提供只依赖Python标准库的离线检查，不借用旧同级主程序虚拟环境。当前命令见 [开发入口](../DEVELOPMENT.md)；本轮脚本测试和现有正式镜像隔离升级结果在本组当前验证，真实HAOS验收另列。

核对：2026-10-12，基线 `41aa5b6`，开始时无未提交变更；本轮仅地图/规则。范围为安装配置、镜像适配、发布与升级责任，不审查主程序内部实现。下面的测试链接是定位；本轮实际运行结果见“验证状态”。

## 按任务定位

| 要改什么 | 入口与关键责任 | 影响与验证入口 |
| --- | --- | --- |
| HA 仓库展示 | [repository.yaml](../../repository.yaml)、[config.yaml](../../ha_bridge/config.yaml) | 插件来源/架构/镜像/webui，核对 Supervisor 安装展示 |
| 挂载与更新渠道 | [config.yaml](../../ha_bridge/config.yaml)、[Dockerfile](../../release/Dockerfile) | /data 与 /run/secrets 持久化；APP_UPDATE_CHANNEL=addon；[流程测试](../../tests/test_release_flow.py) |
| 版本与用户日志 | [version.py](../../release/version.py)：read_current_version、set_version、check_version | 同步 config.yaml 与 [CHANGELOG](../../ha_bridge/CHANGELOG.md)，不能改主程序版本 |
| 正式镜像与标签 | [publish_addon_release.sh](../../release/publish_addon_release.sh) | 读取主镜像不可变 digest，检查双架构和匿名拉取，升级通过再更新 latest/Git |
| 隔离升级 | [verify_addon_upgrade.sh](../../release/verify_addon_upgrade.sh)：start_container、wait_ready | 临时 data/secrets 先旧后新，检查 ready/版本/UID；不能代替 HAOS 真机 |

## 执行与数据路线

`Supervisor → config.yaml 的镜像/挂载/环境 → Add-on Dockerfile → 已发布主镜像原有 entrypoint → HA Bridge`。Dockerfile 不复制业务源码，以 root 初始化后由主镜像入口降权；映射和权限变更会影响用户已有加密凭据与启动。

发布脚本 `preflight|publish`：参数与干净 Git → 查询 origin/main、标签、镜像是否存在 → 解析 BASE_VERSION 主镜像 digest → buildx push 双架构 → 匿名读取 → 临时旧/新镜像升级 → latest → version.py 与 Git。preflight 仍访问远端，不能当离线检查；中途失败不能仅靠已有镜像认定整次发布成功。

此仓库不保存用户业务数据；Supervisor 保管 /data 与 addon_config 映射的 secrets，生命周期由主程序入口和 Supervisor 协同管理。升级脚本用 mktemp 与独立容器，trap 仅清理自己的容器/目录；不操作用户安装数据。

## 修改前要核对的连接

- 改环境或挂载：核对主镜像 entrypoint、Settings 的密钥路径、持久化恢复和 UID，再测旧安装升级。
- 改 BASE_VERSION/修订号：核对主镜像确已发布，config/CHANGELOG/镜像标签同一版本，不能覆盖既有标签。
- 改发布順序：核对匿名拉取和升级失败后 latest/Git 是否保持合理状态；脚本测试与真 Supervisor 分别报告。

## 验证状态与维护

代码关键路线已核对；测试入口：[test_release_flow.py](../../tests/test_release_flow.py)，标准库 `python3 -m unittest discover -s tests -p test_release_flow.py`；shell 语法用 sh -n。本轮上述 4 项测试通过；结果汇总在总工作区初始核验记录。

待实测：真实 Supervisor/HAOS 安装、用户卷权限、恢复与升级。Docker 隔离脚本存在不等于本轮已执行镜像升级。

入口/镜像/挂载/版本责任变化时更新本页和相关安装文档，核对日期及基线随涉及章节更新；纯文案无需重写路线，交接注明原因。开发命令见 [开发入口](../DEVELOPMENT.md)，规则见 [AGENTS](../../AGENTS.md)。

## 2026-11-04 发布恢复与清理反馈

局部基线 `24ac354` 加本轮未提交工具修复。publish_addon_release.sh 增加 resume 动作；[release_state.py](../../release/release_state.py) 归属本组记录/发布事务，保存原 source/previous/base/image/digest。已有镜像只在原摘要匹配时复用，版本提交只允许原源提交后的两个版本文件变化；升级/Git 失败后沿用原 previous，不重复构建或移动已有标签。无摘要的未知推送结果及未提交改动停止人工核对，完成凭证保留。

verify_addon_upgrade.sh 的 EXIT 只清理自己的容器，删除失败保留临时目录并返回非零；SIGINT/SIGTERM/HUP 明确退出，不继续后续发布。正常路径在确认清理成功后才打印完成。行为回归见 [test_release_recovery.py](../../tests/test_release_recovery.py)，覆盖升级/Git 中断、摘要/源码漂移、清理失败和已不存在容器；这些使用本地 Git 和 Docker 替身，不代替 HAOS/镜像实测。tools/check.sh 发现全部本项目 test_*.py。
