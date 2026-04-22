[English](README.md) | **简体中文**

# MyTool

## 产品简介

`MyTool` 是一个面向 Windows 的轻量清理工具。

它围绕一条主链路工作：

`analyze -> review -> dryrun -> delete-safe / restore -> report`

学习模型和安全模型都服务于“更安全、更准确地清理”，不是独立的主功能。

## 核心功能

- `Analyze`：扫描当前发现根并找出清理候选
- `Analyze Fixed`：只扫描固定目标，跳过全盘发现
- `Review`：接受或拒绝新学习到的候选
- `Dry Run`：预览将要清理的内容
- `Delete Safe`：只删除低风险且允许的项目
- `Restore`：从隔离区恢复内容
- `Report`：查看配置、状态、报告和隔离区目录
- `Update`：有新版本时打开最新发布页

## 下载

- 安装版：从 GitHub Releases 下载 `MyTool-v0.1.1-win-x64-setup.exe`
- 便携版：从 GitHub Releases 下载 `MyTool-v0.1.1-win-x64.zip`

安装器说明：

- 安装时会创建桌面和开始菜单入口
- 安装时可选择配置、报告和运行数据目录
- 卸载只移除程序本体；运行数据保留在你选择的数据目录中

## 使用方式

普通用户：

1. 启动 `MyTool`
2. 运行 `Analyze`
3. 如果出现新的学习候选，运行 `Review`
4. 运行 `Dry Run`
5. 运行 `Delete Safe`
6. 只有需要回滚时再用 `Restore`

## 高级用户操作指南

高级用户：

```powershell
mytool
mytool analyze
mytool analyze --fixed-only
mytool review --accept-all
mytool clean --mode dry-run
mytool clean --mode delete --apply --interactive --confirm-delete DELETE
mytool restore --all
mytool config-check
mytool update --open-browser
```

配置文件：

- `config/fixedTargets.json`
- `config/denyRules.json`
- `config/discover.config.json`
- `config/learning.config.json`

## 版本

- `v0.1.1`
