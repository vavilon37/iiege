@echo off
:: Устанавливаем кодировку UTF-8 для корректного ввода русского языка
chcp 65001 >nul

:: Указываем системную переменную для Python, чтобы он всегда работал в UTF-8
set PYTHONIOENCODING=utf-8

title ЕГЭ ИИ Автономный Помощник (Мастер шаблонов)
color 0b

set ROOT=%~dp0
set PYTHON_EXE="D:\WinPython\python-3.11.9.amd64\python.exe"
set MAIN_PY="%ROOT%main.py"

:: Запуск мастера
%PYTHON_EXE% %MAIN_PY%

pause