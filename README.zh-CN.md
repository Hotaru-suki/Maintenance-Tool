[English](README.md) | **简体中文**

# MyTool

## 产品简介

`MyTool` 是一个面向 Windows 的轻量清理工具。

它围绕一条主链路工作：

`scan -> review -> dryrun -> stage -> restore 或 delete-staged`

学习模型和安全模型都服务于“更安全、更准确地清理”，不是独立的主功能。

## 核心功能

- `Scan`：扫描当前发现根并找出清理候选
- `Scan Fixed`：只扫描固定名单，跳过全盘发现
- `Review`：接受或拒绝新学习到的候选
- `Promote Review`：将用户选中的 review 目标转入 fixed 安全名单
- `List Targets`：查看 fixed、review、deny 三类名单
- `Dry Run`：只预演 safe/fixed 目标
- `Stage`：先把 safe/fixed 目标移入可恢复候选区
- `Restore`：从候选区恢复内容
- `Delete Staged`：只永久删除候选区内容
- `Report`：查看配置、状态、报告和候选区目录
- `Update`：有新版本时打开最新发布页

## 下载

- 安装版：从 GitHub Releases 下载 `MyTool-v0.1.2-win-x64-setup.exe`
- 便携版：从 GitHub Releases 下载 `MyTool-v0.1.2-win-x64.zip`

安装器说明：

- 安装时会创建桌面和开始菜单入口
- 安装时可选择配置、报告和运行数据目录
- 卸载只移除程序本体；运行数据保留在你选择的数据目录中

## 使用方式

普通用户：

1. 启动 `MyTool`
2. 运行 `Scan`
3. 如果出现新的学习候选，运行 `Review`
4. 运行 `Dry Run`
5. 运行 `Stage`
6. 需要回滚时运行 `Restore`；确认无误后运行 `Delete Staged`

## 高级用户操作指南

高级用户：

```powershell
mytool
mytool scan
mytool scan-fixed
mytool list-targets --list all
mytool review --accept-all
mytool promote-review --target-id <review-target-id>
mytool dryrun
mytool stage
mytool restore --all
mytool delete-staged --all --confirm-delete DELETE-STAGED
mytool config-check
mytool update --open-browser
```

配置文件：

- `config/fixedTargets.json`
- `config/reviewTargets.json`
- `config/denyRules.json`
- `config/discover.config.json`
- `config/learning.config.json`

## 版本

- `v0.1.2`
