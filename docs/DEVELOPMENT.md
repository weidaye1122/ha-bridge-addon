# Add-on 开发入口

Add-on 是主程序的 HA 安装适配层，源码/Git 分开管理，始终跟随主程序完整发布。它消费对应已发布主镜像，不复制业务源码。关系见 [代码地图](code-map/README.md)。

## 日常验证

在本仓库运行 `sh tools/check.sh`；只依赖 Python 标准库和 shell，无须借用主程序 .venv。覆盖版本/日志、适配 Dockerfile、发布顺序及脚本语法，不查询远端或启动生产。

涉及镜像、权限或持久挂载时再运行 release/verify_addon_upgrade.sh，以明确的上一成功版本和候选版本在临时 data/secrets 上验证。脚本只清理自己创建的容器与目录；Docker 隔离升级不能替代真实 HAOS/Supervisor 安装、Ingress、备份恢复和用户升级。

## 随主程序发布

统一入口是主程序 release/publish_full_release.sh。它先做 Add-on 预检查，主程序发布后再调用本仓库 publish_addon_release.sh publish；Add-on 成功才标记整轮成功。保留 X.Y.Z-N 版本规则以及主镜像不可变 digest、双架构、匿名拉取、升级、latest/Git 的既有校验。

本仓库 preflight 会查询 Git 和镜像；publish 会推送镜像及 Git，均不能作为普通离线检查执行。主程序通过工作区登记或显式 ADDON_REPOSITORY_DIR 找到本仓库，独立克隆也必须明确主程序交付来源。

## 材料与维护

本组记录/当前验证.md 保存有效结果和缺口；必要原始发布身份、主程序联动账本引用和恢复材料保留。旧日常副本及发布工作树保持，后续日常修改在新目录进行；不因旧路径仍在而并行维护两份版本。

config.yaml 的 /data 与 /run/secrets、UID 降权、更新渠道会影响既有用户数据/授权，改动时同时核对主镜像入口。CHANGELOG 和本项目 QA 继续分别维护，不额外新增主程序三项目门禁之外的记录系统。
