#ifndef AppName
  #define AppName "MyTool"
#endif
#ifndef AppExeName
  #define AppExeName "MyTool.exe"
#endif
#ifndef AppIconName
  #define AppIconName "MyTool.ico"
#endif
#ifndef AppVersion
  #define AppVersion "0.1.2"
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
OutputBaseFilename={#AppName}-v{#AppVersion}-win-x64-setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
ChangesEnvironment=yes
DisableProgramGroupPage=yes
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=..\assets\{#AppIconName}
WizardImageStretch=no
DisableDirPage=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Files]
Source: "..\..\dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"

[Registry]
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}'))

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  DataDirPage: TInputDirWizardPage;
  LastDataDirDefault: string;

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

procedure InitializeWizard();
begin
  DataDirPage := CreateInputDirPage(
    wpSelectDir,
    '{#AppName} Data Folder',
    'Choose where {#AppName} stores config, reports, and runtime data.',
    'This folder can be inside the install directory or any writable location.',
    False,
    ''
  );
  DataDirPage.Add('');
  LastDataDirDefault := ExpandConstant('{app}\workspace');
  DataDirPage.Values[0] := LastDataDirDefault;
end;

procedure CurPageChanged(CurPageID: Integer);
var
  CurrentDefault: string;
begin
  if CurPageID <> DataDirPage.ID then
    exit;

  CurrentDefault := ExpandConstant('{app}\workspace');
  if (Trim(DataDirPage.Values[0]) = '') or (DataDirPage.Values[0] = LastDataDirDefault) then
  begin
    DataDirPage.Values[0] := CurrentDefault;
  end;
  LastDataDirDefault := CurrentDefault;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  WorkspaceRootPath: string;
begin
  if CurStep <> ssInstall then
    exit;

  WorkspaceRootPath := Trim(DataDirPage.Values[0]);
  if WorkspaceRootPath = '' then
    WorkspaceRootPath := ExpandConstant('{app}\workspace');

  ForceDirectories(WorkspaceRootPath);
  SaveStringToFile(
    ExpandConstant('{app}\workspace-root.txt'),
    WorkspaceRootPath + #13#10,
    False
  );
end;
