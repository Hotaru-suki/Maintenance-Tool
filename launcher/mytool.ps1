param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

& "$PSScriptRoot\MyTool.exe" @ArgsList
