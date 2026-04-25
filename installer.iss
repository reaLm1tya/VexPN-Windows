; Офлайн-установщик (Inno): всё внутри одного exe. Альтернатива: скачивание с Git — dist\\VexPN-Setup.exe + install_manifest.json
; (по умолчанию %LocalAppData%\\VexPN, без UAC; нужны dist\\VexPN.exe, dist\\sing-box.exe — build.ps1)

#define MyAppName "VexPN"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "VexPN"
#define MyAppURL "https://github.com/reaLm1tya/VexPN-Windows"
#define MyAppExeName "VexPN.exe"
#define MySingBox "sing-box.exe"

[Setup]
AppId={{C7F3A1B2-4D5E-4F6A-9B0C-1D2E3F4A5B6C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL=https://github.com/reaLm1tya/VexPN-Windows/issues
DefaultDirName={localappdata}\VexPN
Uninstallable=yes
CreateUninstallRegKey=yes
DefaultGroupName={#MyAppName}
DisableDirPage=no
OutputDir=installer_output
OutputBaseFilename={#MyAppName}-Windows-Setup-{#MyAppVersion}
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64os

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
; Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\{#MySingBox}"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "dist\UninstallVexPN.exe"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Удалить VexPN"; Filename: "{app}\UninstallVexPN.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить VexPN"; Flags: nowait postinstall skipifsilent
