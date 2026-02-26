Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "scripts\start_server.bat" & Chr(34), 0
Set WshShell = Nothing
