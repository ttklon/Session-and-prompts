; Inno Setup 6.x — компилируется ТОЛЬКО на Windows командой:
;   iscc installer.iss
; На выходе — единый setup_GensparkArkhivator.exe с рабочим столом и меню Пуск.

[Setup]
AppName=Genspark Arkhivator
AppVersion=2.0
DefaultDirName={autopf}\GensparkArkhivator
DefaultGroupName=Genspark Arkhivator
OutputBaseFilename=setup_GensparkArkhivator
Compression=lzma
SolidCompression=yes

[Files]
Source: "..\dist\GensparkArkhivator\*"; DestDir: "{app}"; Flags: recursesubdirs
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\selectors.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README_ru.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Genspark Arkhivator"; Filename: "{app}\GensparkArkhivator.exe"
Name: "{group}\Архив (открыть папку программы)"; Filename: "{app}"
Name: "{autodesktop}\Genspark Arkhivator"; Filename: "{app}\GensparkArkhivator.exe"

[Run]
Filename: "{app}\install_python_deps.bat"; Description: "Установить библиотеки (один раз)"; Flags: nowait postinstall skipifsilent
Filename: "{app}\GensparkArkhivator.exe"; Description: "Запустить программу"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup: Boolean;
begin
  Result := True;
end;
