@echo off
REM اسکریپت اجرای Django برای Windows Service
cd /d "D:\Design & Source Code\Source Coding\BudgetsSystem"
"D:\Python312\python.exe" manage.py runserver 0.0.0.0:8000
