**English** | [简体中文](README.zh-CN.md)

# MaintenanceTool

## Overview

`MaintenanceTool` is a lightweight Windows local maintenance tool for safe, reviewable cleanup of common caches and temporary files.

It provides two usage modes:
- Ordinary user mode: GUI / guided menu
- Advanced user mode: direct CLI

## Features

- `Analyze`: scan and discover learnable or removable targets
- `Review Pending`: review learning suggestions before promotion
- `Dry Run`: preview cleanup without deleting anything
- `Delete Safe`: execute only low-risk cleanup actions
- `Restore`: restore items from quarantine
- `Check Updates`: open the latest release download page
- `Feedback`: open a prefilled GitHub Issue page with email fallback

## Download

Recommended for ordinary users:
- Open the GitHub Releases page
- Download the Windows installer `MaintenanceTool-v0.1.0-win-x64-setup.exe`
- Install it and then either:
- double-click `MaintenanceTool.exe` to enter the terminal interface
- open a new terminal and run `mtool`

Optional for advanced users:
- Download the portable package `MaintenanceTool-v0.1.0-win-x64.zip`
- Prefer `winget` after the package is published to the Windows Package Manager community repository

## Usage

Ordinary users:
1. Launch `MaintenanceTool.exe` or run `mtool`
2. Start with `Analyze`
3. If suggestions appear, use `Review Pending`
4. Run `Dry Run`
5. Confirm and continue with `Delete Safe`
6. Use `Restore` if rollback is needed

## Advanced User Guide

Common commands:

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

Configuration files:
- `config/fixedTargets.json`
- `config/denyRules.json`
- `config/discover.config.json`
- `config/learning.config.json`

Packaged Windows builds keep mutable runtime data in a visible folder such as `Documents\MaintenanceTool`.

Modern install options for advanced users:

```powershell
winget search MaintenanceTool
```

After the package is published to the winget community repository, install it from the search result in the usual `winget` flow.

If the package has not been published to the winget community repository yet, use the release installer directly.

Local winget manifest install from a downloaded release directory:

```powershell
winget install --manifest .\MaintenanceTool-v0.1.0-win-x64-winget.yaml
```

## Version

- `v0.1.0`
