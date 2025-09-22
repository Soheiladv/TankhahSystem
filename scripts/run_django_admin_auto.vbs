
' اسکریپت VBS برای اجرای خودکار Django با دسترسی ادمین
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' مسیر پروژه
strProjectPath = "D:\Design & Source Code\Source Coding\BudgetsSystem"
strPythonPath = "D:\Python312\python.exe"
strManagePath = strProjectPath & "\manage.py"

' بررسی وجود فایل‌ها
If Not objFSO.FileExists(strManagePath) Then
    MsgBox "فایل manage.py یافت نشد: " & strManagePath, vbCritical, "خطا"
    WScript.Quit
End If

If Not objFSO.FileExists(strPythonPath) Then
    MsgBox "Python یافت نشد: " & strPythonPath, vbCritical, "خطا"
    WScript.Quit
End If

' نمایش پیام شروع
MsgBox "🚀 در حال اجرای Django با دسترسی ادمین..." & vbCrLf & vbCrLf & _
       "⚠️ توجه: این اسکریپت Django را با دسترسی ادمین اجرا می‌کند" & vbCrLf & vbCrLf & _
       "🌐 سرور در آدرس زیر در دسترس خواهد بود:" & vbCrLf & _
       "    http://127.0.0.1:8000/" & vbCrLf & vbCrLf & _
       "🔐 برای مدیریت USB Dongle:" & vbCrLf & _
       "    http://127.0.0.1:8000/usb-key-validator/enhanced/", _
       vbInformation, "Django USB Dongle Server"

' دستور اجرای Django
strCommand = "cmd /c cd /d """ & strProjectPath & """ && """ & strPythonPath & """ manage.py runserver 0.0.0.0:8000"

' اجرای دستور با دسترسی ادمین
On Error Resume Next
Set objExec = objShell.Exec("runas /user:Administrator """ & strCommand & """")
If Err.Number <> 0 Then
    ' اگر runas کار نکرد، از PowerShell استفاده کن
    strPowerShellCommand = "Start-Process powershell -Verb RunAs -ArgumentList '-Command cd """ & strProjectPath & """; """ & strPythonPath & """ manage.py runserver 0.0.0.0:8000'"
    objShell.Run strPowerShellCommand, 1, False
End If
On Error GoTo 0

' نمایش پیام پایان
MsgBox "✅ Django Server شروع شد!" & vbCrLf & vbCrLf & _
       "🌐 سرور در آدرس زیر در دسترس است:" & vbCrLf & _
       "    http://127.0.0.1:8000/" & vbCrLf & vbCrLf & _
       "🔐 برای مدیریت USB Dongle:" & vbCrLf & _
       "    http://127.0.0.1:8000/usb-key-validator/enhanced/", _
       vbInformation, "Django USB Dongle Server - Ready"
