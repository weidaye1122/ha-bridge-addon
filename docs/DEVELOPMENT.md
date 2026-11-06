# Add-on 开发入口

Add-on 是主程序的 HA 安装适配层，源码/Git 分开管理，始终跟随主程序完整发布。它消费对应已发布主镜像，不复制业务源码。关系见 [代码地图](code-map/README.md)。

## 日常验证

在本仓库运行 `sh tools/check.sh`；只依赖 Python 标准库和 shell，无须借用主程序 .venv。覆盖版本/日志、适配 Dockerfile、发布顺序及脚本语法，不查询远端或启动生产。

涉及镜像、权限或持久挂载时再运行 release/verify_addon_upgrade.sh，以明确的上一成功版本和候选版本在临时 data/secrets 上验证。脚本只清理自己创建的容器与目录；Docker 隔离升级不能替代真实 HAOS/Supervisor 安装、Ingress、备份恢复和用户升级。

## 随主程序发布

统一入口是主程序release/publish_full_release.sh。新发布先prepare主程序和Add-on不可变候选，验证后check本版任务/用户/必需验收，最后publish提升同一摘要；Add-on直接以阿里云候选主镜像repo@digest构建，无须提前发布主程序正式标签。整轮成功必须等正式镜像、两个Git和商店版本全部回查。X.Y.Z-N策略、挂载、UID和业务代码责任不变。

[release/candidate.py](../release/candidate.py)提供prepare/inspect/finalize/abandon公开协作入口，由主程序调用；本组记录/发布事务保存format2候选来源、上一成功升级源、主镜像基线、镜像摘要和版本Git状态，CLI写操作持单次锁。prepare只写专用候选引用并验证双架构、匿名拉取和升级，不更新正式渠道或商店。finalize需所属主程序完整事务授权，并确认正式Add-on渠道已经指向已验证摘要，再提交版本配置/Git。主程序不复制本项目版本/恢复规则，候选source或摘要漂移均停止；已发生正式提升时不能abandon。

升级脚本用上一成功版本生成非空匿名账号/项目/草稿，核对已有会话及密码登录、实例/身份文件、业务表、重启和备份恢复；digest引用必须显式给出旧应用版本，VERIFY_PLATFORM分别指定amd64/arm64。输出的执行平台必须如实说明，本机仿真或容器不能代替真实HAOS/Supervisor安装、Ingress及用户卷恢复。只清理自身容器/临时目录，容器删除失败保留精确路径并返回失败。

旧publish_addon_release.sh仍提供只读远端preflight和format1 resume，新单独publish拒绝以免绕过整轮门禁。若旧主程序已发布而Add-on尚未开始，只有匹配源码/版本/主镜像摘要的所属format1完整凭证可以授权补完该历史尾段。旧恢复必须使用其原源码基线，不能用新工具提交改写旧receipt身份。完整凭证保留，不作为普通缓存删除；新事务恢复通过主程序resume同一版本，不覆盖未知镜像或重建已验证产物。

preflight、候选prepare都会查询Git/镜像，prepare还上传候选，只在相应授权下执行；日常离线检查仍是sh tools/check.sh。主程序通过项目登记或显式ADDON_REPOSITORY_DIR定位本仓库；独立克隆明确主程序与本组记录位置。当前真实运行/平台边界见所属当前验证，本轮工具改动没有执行新正式发布。

## 材料与维护

本组记录/当前验证.md 保存有效结果和缺口；必要原始发布身份、主程序联动账本引用和恢复材料保留。登记的旧来源及工作树路径已失效；历史源码恢复以新 Git 可读提交核对，日常修改只在新目录进行。

config.yaml 的 /data 与 /run/secrets、UID 降权、更新渠道会影响既有用户数据/授权，改动时同时核对主镜像入口。CHANGELOG 和本项目 QA 继续分别维护，不额外新增主程序三项目门禁之外的记录系统。
