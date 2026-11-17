#define MyAppName "PianoCapture"
#define MyAppVersion "1.16"
#define MyAppExeName "PianoCapture.exe"
#define MyAppId "{{67B3B8E5-4757-4A1D-8056-8AD06F83FC37}"
#define RepoRoot "..\.."
#define PackageDir RepoRoot + "\build\piano-win\PianoCapture"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=AI TabTool
AppPublisherURL=https://github.com/teppoaland/tabtool
DefaultDirName={localappdata}\Programs\PianoCapture
DefaultGroupName=PianoCapture
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#RepoRoot}\dist
OutputBaseFilename=PianoCapture-Setup
SetupIconFile={#PackageDir}\piano.ico
UninstallDisplayIcon={app}\PianoCapture.exe
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion=1.16.0.0
VersionInfoDescription=PianoCapture installer
VersionInfoProductName=PianoCapture
VersionInfoProductVersion=1.16.0.0
LicenseFile={#RepoRoot}\LICENSE

[Languages]
Name: "finnish"; MessagesFile: "compiler:Languages\Finnish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "{#PackageDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#RepoRoot}\piano\win\Kayttoohje.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\PianoCapture"; Filename: "{app}\PianoCapture.exe"; WorkingDir: "{app}"; IconFilename: "{app}\piano.ico"
Name: "{autoprograms}\PianoCapture - Kayttoohje"; Filename: "{app}\Kayttoohje.txt"
Name: "{autodesktop}\PianoCapture"; Filename: "{app}\PianoCapture.exe"; WorkingDir: "{app}"; IconFilename: "{app}\piano.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\PianoCapture.exe"; Description: "{cm:LaunchProgram,PianoCapture}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\runtime"
