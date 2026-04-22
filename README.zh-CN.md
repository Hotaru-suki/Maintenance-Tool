[English](README.md) | **简体中文**

# MaintenanceTool

## 产品简介

`MaintenanceTool` 是一个面向 Windows 的轻量本地维护工具，用于安全、可回看、可确认地清理常见缓存与临时内容。

它提供两种使用方式：
- 普通用户模式：图形界面 / 引导式菜单
- 高级用户模式：命令行直接操作

## 主要功能

- `Analyze`：扫描并发现可学习、可清理的目标
- `Review Pending`：审核学习建议，决定是否纳入规则
- `Dry Run`：预览清理计划，不执行删除
- `Delete Safe`：仅执行低风险、允许范围内的安全删除
- `Restore`：恢复隔离区中的内容
- `Check Updates`：打开最新版本下载页
- `Feedback`：打开 GitHub Issue 反馈页，失败时回退到作者邮箱

## 如何下载

普通用户推荐：
- 打开 GitHub Releases 页面
- 下载 Windows 安装包 `MaintenanceTool-v0.1.0-win-x64-setup.exe`
- 安装后可任选以下方式启动：
- 双击 `MaintenanceTool.exe` 进入终端交互界面
- 打开新的终端后直接运行 `mtool`

高级用户可选：
- 下载便携版 `MaintenanceTool-v0.1.0-win-x64.zip`
- 在包正式发布到 Windows Package Manager 社区仓库后，优先使用 `winget`

## 如何使用

普通用户：
1. 启动 `MaintenanceTool.exe` 或运行 `mtool`
2. 先执行 `Analyze`
3. 如有建议，执行 `Review Pending`
4. 执行 `Dry Run`
5. 确认后执行 `Delete Safe`
6. 如有需要，使用 `Restore` 恢复

## 高级用户操作指南

常用命令：

```bash
mtool
mtool analyze --config-dir config --state-dir state
mtool review-pending --config-dir config --state-dir state --accept-all
mtool clean --config-dir config --report-dir reports --mode dry-run
mtool clean --config-dir config --report-dir reports --mode quarantine --apply
mtool clean --config-dir config --report-dir reports --mode delete --apply --interactive --confirm-delete DELETE
mtool restore-quarantine --quarantine-dir .quarantine
mtool config-check --config-dir config
mtool check-update --state-dir state --open-browser
mtool feedback --config-dir config --state-dir state --report-dir reports --category bug --title "..." --details "..."
mtool verify-sandbox --sandbox-root <path>
```

配置文件：
- `config/fixedTargets.json`
- `config/denyRules.json`
- `config/discover.config.json`
- `config/learning.config.json`

Windows 打包版本默认将运行数据放在可见目录，例如 `Documents\MaintenanceTool`。

高级用户更现代的安装方式：

```powershell
winget search MaintenanceTool
```

发布到 winget 社区仓库后，可直接从搜索结果中按正常 `winget` 流程安装。

如果该包尚未发布到 winget 社区仓库，则继续使用 Release 安装器。

从已下载的发布目录直接用本地 winget manifest 安装：

```powershell
winget install --manifest .\MaintenanceTool-v0.1.0-win-x64-winget.yaml
```

## 版本

- `v0.1.0`
