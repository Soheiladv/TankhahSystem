#!/bin/bash
# auto-mcp.sh – تغییرات خودکار کد با Claude Code
echo "شروع review خودکار..."
claude review . --apply  # review و apply تغییرات (اگر approvals ست کنی)

echo "Refactor فایل‌های اصلی..."
claude refactor /*.py  # refactor خودکار

echo "تست و کامیت..."
pytest  # تست‌ها رو اجرا کن
if [ $? -eq 0 ]; then
  git add .
  git commit -m "Auto-refactor by Claude Code [skip ci]"
  git push
  echo "PR آماده – دستی merge کن"
fi