' اسکریپت VBS برای اجرای خودکار Django به عنوان Administrator
' این اسکریپت خودش دسترسی ادمین را درخواست می‌کند

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' نمایش پیام شروع
MsgBox "🚀 در حال اجرای Django به عنوان Administrator..." & vbCrLf & vbCrLf & _
       "⚠️ توجه: برای دسترسی کامل به USB Dongle، Django باید به عنوان Administrator اجرا شود" & vbCrLf & vbCrLf & _
       "🌐 سرور در آدرس زیر در دسترس خواهد بود:" & vbCrLf & _
       "    http://127.0.0.1:8000/" & vbCrLf & vbCrLf & _
       "🔐 برای مدیریت USB Dongle:" & vbCrLf & _
       "    http://127.0.0.1:8000/usb-key-validator/enhanced/" & vbCrLf & vbCrLf & _
       "📊 برای داشبورد:" & vbCrLf & _
       "    http://127.0.0.1:8000/usb-key-validator/dashboard/", _
       vbInformation, "Django USB Dongle Server"

' مسیر پروژه
strProjectPath = "D:\Design & Source Code\Source Coding\BudgetsSystem"

' دستور اجرای Django
strCommand = "cmd /c cd /d """ & strProjectPath & """ && python manage.py runserver"

' اجرای دستور با دسترسی ادمین
On Error Resume Next
Set objExec = objShell.Exec("runas /user:Administrator """ & strCommand & """")
If Err.Number <> 0 Then
    ' اگر runas کار نکرد، از PowerShell استفاده کن
    strPowerShellCommand = "Start-Process powershell -Verb RunAs -ArgumentList '-Command cd """ & strProjectPath & """; python manage.py runserver'"
    objShell.Run strPowerShellCommand, 1, False
End If
On Error GoTo 0

' نمایش پیام پایان
MsgBox "✅ Django Server شروع شد!" & vbCrLf & vbCrLf & _
       "🌐 سرور در آدرس زیر در دسترس است:" & vbCrLf & _
       "    http://127.0.0.1:8000/" & vbCrLf & vbCrLf & _
       "🔐 برای مدیریت USB Dongle:" & vbCrLf & _
       "    http://127.0.0.1:8000/usb-key-validator/enhanced/" & vbCrLf & vbCrLf & _
       "📊 برای داشبورد:" & vbCrLf & _
       "    http://127.0.0.1:8000/usb-key-validator/dashboard/", _
       vbInformation, "Django USB Dongle Server - Ready"
