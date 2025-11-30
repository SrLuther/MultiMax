[Setup]
AppName=MultiMax
AppVersion=1.0
DefaultDirName={pf}\MultiMax
DefaultGroupName=MultiMax
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
OutputDir=dist
OutputBaseFilename=MultiMax-Setup

[Files]
Source: "dist\MultiMax.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\MultiMax"; Filename: "{app}\MultiMax.exe"
Name: "{group}\Desinstalar MultiMax"; Filename: "{uninstallexe}"

[Run]
Filename: "{cmd}"; Parameters: "/C netsh advfirewall firewall add rule name=\"MultiMax5000\" dir=in action=allow protocol=TCP localport=5000"; Flags: runhidden; StatusMsg: "Configurando firewall..."
Filename: "{app}\MultiMax.exe"; Description: "Iniciar MultiMax"; Flags: postinstall nowait skipifsilent
