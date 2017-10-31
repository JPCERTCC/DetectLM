:: Windows command (cmd.exe) logging tool
::
:: How To Use
:: 1. Create bat file
::    [Filder Name]\cmdlogs.bat
::
:: 2. Set autorun setting
::    reg add "HKEY_CURRENT_USER\Software\Microsoft\Command Processor" /v AutoRun /d [Filder Name]\cmdlogs.bat
::    or
::    reg add "HKEY_LOCAL_MACHINE\Software\Microsoft\Command Processor" /v AutoRun /d [Filder Name]\cmdlogs.bat
::

@echo off
setlocal EnableDelayedExpansion
set LogFolderName=%LOCALAPPDATA%\CMDLogs
set LogFileName=%date:~0,4%%date:~5,2%%date:~8,2%.log

IF NOT EXIST %LogFolderName% (md %LogFolderName%)
IF NOT EXIST %LogFolderName%\%LogFileName% (echo timestamp,command>> %LogFolderName%\%LogFileName%)

:getcmd
set Command=
set DateTime=%date:~0,4%-%date:~5,2%-%date:~8,2% %time:~0,2%:%time:~3,2%:%time:~6,2%
set /P Command=%cd%^>
echo %DateTime%,!Command!>> %LogFolderName%\%LogFileName%
call %Command%
goto getcmd
