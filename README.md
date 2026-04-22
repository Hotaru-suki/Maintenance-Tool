**English** | [简体中文](README.zh-CN.md)

# MyTool

## Overview

`MyTool` is a lightweight Windows cleanup tool.

It is built around one main flow:

`analyze -> review -> dryrun -> delete-safe / restore -> report`

Learning and safety rules exist to make cleanup safer and more accurate. They are not separate product goals.

## What It Does

- `Analyze`: scan current discover roots and find cleanup candidates
- `Analyze Fixed`: scan only fixed targets and skip full discovery
- `Review`: accept or reject newly learned candidates
- `Dry Run`: preview what would be cleaned
- `Delete Safe`: delete only low-risk allowed items
- `Restore`: recover items from quarantine
- `Report`: open runtime folders for config, state, reports, and quarantine
- `Update`: open the latest release page when a newer version exists

## Download

- Installer: download `MyTool-v0.1.1-win-x64-setup.exe` from GitHub Releases
- Portable: download `MyTool-v0.1.1-win-x64.zip` from GitHub Releases

Installer notes:

- setup creates desktop and Start Menu entries
- setup lets you choose the data folder for config, reports, and runtime state
- uninstall removes the installed app; runtime data stays in the folder you selected

## Use

Ordinary users:

1. Launch `MyTool`
2. Run `Analyze`
3. If new learned candidates appear, run `Review`
4. Run `Dry Run`
5. Run `Delete Safe`
6. Use `Restore` only if rollback is needed

## Advanced User Guide

Advanced users:

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

Configuration:

- `config/fixedTargets.json`
- `config/denyRules.json`
- `config/discover.config.json`
- `config/learning.config.json`

## Version

- `v0.1.1`
