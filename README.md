**English** | [简体中文](README.zh-CN.md)

# MyTool

## Overview

`MyTool` is a lightweight Windows cleanup tool.

It is built around one main flow:

`scan -> review -> dryrun -> stage -> restore or delete-staged`

Learning and safety rules exist to make cleanup safer and more accurate. They are not separate product goals.

## What It Does

- `Scan`: scan current discover roots and find cleanup candidates
- `Scan Fixed`: scan only fixed targets and skip full discovery
- `Review`: accept or reject newly learned candidates
- `Promote Review`: move selected review targets into the fixed safe list
- `List Targets`: show fixed, review, and deny lists
- `Dry Run`: preview safe fixed targets only
- `Stage`: move safe fixed targets into a recoverable staged area
- `Restore`: recover staged items
- `Delete Staged`: permanently delete only staged items
- `Report`: open runtime folders for config, state, reports, and staged data
- `Update`: open the latest release page when a newer version exists

## Download

- Installer: download `MyTool-v0.1.2-win-x64-setup.exe` from GitHub Releases
- Portable: download `MyTool-v0.1.2-win-x64.zip` from GitHub Releases

Installer notes:

- setup creates desktop and Start Menu entries
- setup lets you choose the data folder for config, reports, and runtime state
- uninstall removes the installed app; runtime data stays in the folder you selected

## Use

Ordinary users:

1. Launch `MyTool`
2. Run `Scan`
3. If new learned candidates appear, run `Review`
4. Run `Dry Run`
5. Run `Stage`
6. Use `Restore` to roll back, or `Delete Staged` to permanently remove staged items

## Advanced User Guide

Advanced users:

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

Configuration:

- `config/fixedTargets.json`
- `config/reviewTargets.json`
- `config/denyRules.json`
- `config/discover.config.json`
- `config/learning.config.json`

## Version

- `v0.1.2`
