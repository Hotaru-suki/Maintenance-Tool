param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

& "$PSScriptRoot\MaintenanceTool.exe" @ArgsList
