#define AppName "MaintenanceTool"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{8D2D3BE6-3A3B-4ACF-87E7-6BA2E1C4A301}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Hotaru-suki
AppPublisherURL=https://github.com/Hotaru-suki/Maintenance-Tool
AppSupportURL=https://github.com/Hotaru-suki/Maintenance-Tool/issues
AppUpdatesURL=https://github.com/Hotaru-suki/Maintenance-Tool/releases/latest
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=..\..\dist
OutputBaseFilename=MaintenanceTool-v{#AppVersion}-win-x64-setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
ChangesEnvironment=yes
DisableProgramGroupPage=no
PrivilegesRequired=admin
UninstallDisplayIcon={app}\MaintenanceTool.exe
SetupIconFile=..\assets\MaintenanceTool.ico
WizardImageStretch=no
DisableDirPage=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Files]
Source: "..\..\dist\MaintenanceTool\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MaintenanceTool"; Filename: "{app}\MaintenanceTool.exe"
Name: "{autodesktop}\MaintenanceTool"; Filename: "{app}\MaintenanceTool.exe"; Tasks: desktopicon
Name: "{group}\Uninstall MaintenanceTool"; Filename: "{uninstallexe}"

[Registry]
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}'))

[Run]
Filename: "{app}\MaintenanceTool.exe"; Description: "Launch MaintenanceTool"; Flags: nowait postinstall skipifsilent

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Uppercase(Param) + ';', ';' + Uppercase(OrigPath) + ';') = 0;
end;
