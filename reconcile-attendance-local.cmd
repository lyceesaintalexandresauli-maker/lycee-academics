@echo off
call "%~dp0backend-app\reconcile-attendance-local.cmd"
exit /b %ERRORLEVEL%
