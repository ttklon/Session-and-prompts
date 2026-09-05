; Inno Setup script для Genspark Arkhivator
; Собирается в Action шаге jossef/action-inno-setup: пользователь получает
; setup.exe с ярлыком «Genspark Arkhivator» на рабочем столе и в меню Пуск.
#define MyAppName "Genspark Arkhivator"
#define MyAppVersion "0.5"
#define MyAppPublisher "Asma"
#define MyAppURL "https://github.com/ttklon/Session-and-prompts"
#define MyAppExeName "genspark_arkhivator.exe"

[Setup]
AppId={{A3F9C4E2-A2B7-4E36-B2D1-5C5A4F7B9D61}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=
OutputDir=..\dist_installer
OutputBaseFilename=genspark_arkhivator_setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "..\dist\genspark_arkhivator.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\selectors.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\reference_screenshot.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
