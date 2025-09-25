#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت پیشرفته ارسال خودکار به گیت‌هاب با تحلیل تغییرات و پیام‌های هوشمند فارسی
Smart Git Push with Intelligent Persian Commit Messages

استفاده:
    python scripts/smart_git_push.py --message "توضیح دلخواه"
    python scripts/smart_git_push.py --auto
    python scripts/smart_git_push.py --dry-run
"""

import subprocess
import sys
import os
import argparse
from datetime import datetime
from pathlib import Path
import re
from typing import Dict, List, Tuple, Optional

class SmartGitPush:
    def __init__(self):
        self.repo_root = self._find_repo_root()
        self.branch = self._get_current_branch()
        self.now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
    def _find_repo_root(self) -> Path:
        """پیدا کردن ریشه پروژه"""
        current = Path.cwd()
        while current != current.parent:
            if (current / '.git').exists():
                return current
            current = current.parent
        raise FileNotFoundError("پوشه .git پیدا نشد")
    
    def _get_current_branch(self) -> str:
        """دریافت نام شاخه جاری"""
        try:
            result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                                  capture_output=True, text=True, cwd=self.repo_root)
            return result.stdout.strip() or 'main'
        except:
            return 'main'
    
    def _run_git_command(self, command: List[str]) -> Tuple[str, str, int]:
        """اجرای دستور git"""
        try:
            result = subprocess.run(command, capture_output=True, text=True, cwd=self.repo_root)
            return result.stdout, result.stderr, result.returncode
        except FileNotFoundError:
            print("❌ خطا: git نصب نیست یا در PATH نیست.")
            sys.exit(1)
    
    def _analyze_changes(self) -> Dict:
        """تحلیل تغییرات و دسته‌بندی فایل‌ها"""
        stdout, stderr, code = self._run_git_command(['git', 'status', '--porcelain'])
        
        if code != 0:
            print(f"❌ خطا در دریافت وضعیت git: {stderr}")
            sys.exit(1)
        
        changes = {
            'added': [],
            'modified': [],
            'deleted': [],
            'renamed': [],
            'untracked': [],
            'total_files': 0,
            'total_changes': 0
        }
        
        lines = [line for line in stdout.split('\n') if line.strip()]
        
        for line in lines:
            status = line[:2]
            filename = line[3:].strip()
            
            if status.startswith('??'):
                changes['untracked'].append(filename)
            elif status.startswith('A'):
                changes['added'].append(filename)
            elif status.startswith('M'):
                changes['modified'].append(filename)
            elif status.startswith('D'):
                changes['deleted'].append(filename)
            elif status.startswith('R'):
                changes['renamed'].append(filename)
        
        changes['total_files'] = len(lines)
        changes['total_changes'] = len(changes['added']) + len(changes['modified']) + len(changes['deleted'])
        
        return changes
    
    def _categorize_files(self, files: List[str]) -> Dict[str, List[str]]:
        """دسته‌بندی فایل‌ها بر اساس نوع"""
        categories = {
            'templates': [],
            'models': [],
            'views': [],
            'forms': [],
            'urls': [],
            'migrations': [],
            'static': [],
            'media': [],
            'scripts': [],
            'tests': [],
            'config': [],
            'docs': [],
            'other': []
        }
        
        for file_path in files:
            path = Path(file_path)
            
            if 'templates' in str(path):
                categories['templates'].append(file_path)
            elif 'models.py' in str(path) or 'model' in str(path).lower():
                categories['models'].append(file_path)
            elif 'views' in str(path).lower() or 'view' in str(path).lower():
                categories['views'].append(file_path)
            elif 'forms.py' in str(path) or 'form' in str(path).lower():
                categories['forms'].append(file_path)
            elif 'urls.py' in str(path):
                categories['urls'].append(file_path)
            elif 'migrations' in str(path):
                categories['migrations'].append(file_path)
            elif 'static' in str(path):
                categories['static'].append(file_path)
            elif 'media' in str(path):
                categories['media'].append(file_path)
            elif 'scripts' in str(path) or 'script' in str(path).lower():
                categories['scripts'].append(file_path)
            elif 'test' in str(path).lower():
                categories['tests'].append(file_path)
            elif any(x in str(path).lower() for x in ['settings', 'config', 'requirements']):
                categories['config'].append(file_path)
            elif any(x in str(path).lower() for x in ['readme', 'docs', '.md']):
                categories['docs'].append(file_path)
            else:
                categories['other'].append(file_path)
        
        return categories
    
    def _generate_change_summary(self, changes: Dict) -> str:
        """تولید خلاصه تغییرات"""
        summary_parts = []
        
        if changes['added']:
            summary_parts.append(f"➕ {len(changes['added'])} فایل جدید")
        if changes['modified']:
            summary_parts.append(f"✏️ {len(changes['modified'])} فایل ویرایش شده")
        if changes['deleted']:
            summary_parts.append(f"🗑️ {len(changes['deleted'])} فایل حذف شده")
        if changes['renamed']:
            summary_parts.append(f"🔄 {len(changes['renamed'])} فایل تغییر نام")
        if changes['untracked']:
            summary_parts.append(f"📁 {len(changes['untracked'])} فایل جدید")
        
        return " | ".join(summary_parts) if summary_parts else "بدون تغییر"
    
    def _generate_file_categories_summary(self, changes: Dict) -> str:
        """تولید خلاصه دسته‌بندی فایل‌ها"""
        all_files = changes['added'] + changes['modified'] + changes['deleted'] + changes['renamed']
        categories = self._categorize_files(all_files)
        
        category_summary = []
        category_names = {
            'templates': 'تمپلیت‌ها',
            'models': 'مدل‌ها',
            'views': 'ویوها',
            'forms': 'فرم‌ها',
            'urls': 'URLها',
            'migrations': 'مایگریشن‌ها',
            'static': 'فایل‌های استاتیک',
            'media': 'رسانه‌ها',
            'scripts': 'اسکریپت‌ها',
            'tests': 'تست‌ها',
            'config': 'تنظیمات',
            'docs': 'مستندات',
            'other': 'سایر'
        }
        
        for category, files in categories.items():
            if files:
                category_summary.append(f"{category_names[category]}: {len(files)}")
        
        return " | ".join(category_summary) if category_summary else ""
    
    def _detect_major_changes(self, changes: Dict) -> List[str]:
        """تشخیص تغییرات مهم"""
        major_changes = []
        
        all_files = changes['added'] + changes['modified'] + changes['deleted']
        
        # بررسی تغییرات مهم
        if any('migrations' in f for f in all_files):
            major_changes.append("🔄 تغییرات دیتابیس")
        
        if any('models.py' in f for f in all_files):
            major_changes.append("📊 تغییرات مدل‌ها")
        
        if any('views' in f.lower() for f in all_files):
            major_changes.append("🎯 تغییرات ویوها")
        
        if any('forms.py' in f for f in all_files):
            major_changes.append("📝 تغییرات فرم‌ها")
        
        if any('templates' in f for f in all_files):
            major_changes.append("🎨 تغییرات UI")
        
        if any('static' in f for f in all_files):
            major_changes.append("🎨 تغییرات استایل‌ها")
        
        if any('test' in f.lower() for f in all_files):
            major_changes.append("🧪 تغییرات تست‌ها")
        
        if any('requirements' in f.lower() or 'settings' in f.lower() for f in all_files):
            major_changes.append("⚙️ تغییرات پیکربندی")
        
        return major_changes
    
    def _generate_commit_message(self, changes: Dict, custom_message: str = "") -> str:
        """تولید پیام کمیت هوشمند"""
        change_summary = self._generate_change_summary(changes)
        file_categories = self._generate_file_categories_summary(changes)
        major_changes = self._detect_major_changes(changes)
        
        # عنوان کمیت
        if major_changes:
            title = f"feat: {', '.join(major_changes)} - {self.now}"
        elif changes['total_changes'] > 10:
            title = f"feat: به‌روزرسانی گسترده پروژه - {self.now}"
        elif changes['total_changes'] > 0:
            title = f"update: به‌روزرسانی پروژه - {self.now}"
        else:
            title = f"chore: به‌روزرسانی خودکار - {self.now}"
        
        # بدنه پیام
        body_lines = [
            f"📅 تاریخ: {self.now}",
            f"🌿 شاخه: {self.branch}",
            f"📊 آمار: {change_summary}",
        ]
        
        if file_categories:
            body_lines.append(f"📁 دسته‌بندی: {file_categories}")
        
        if major_changes:
            body_lines.append(f"🎯 تغییرات مهم: {', '.join(major_changes)}")
        
        if custom_message:
            body_lines.append(f"💬 توضیحات: {custom_message}")
        
        # فایل‌های مهم
        important_files = []
        all_files = changes['added'] + changes['modified']
        
        for file_path in all_files[:10]:  # حداکثر 10 فایل
            if any(keyword in file_path.lower() for keyword in ['model', 'view', 'form', 'url', 'migration']):
                important_files.append(f"  • {file_path}")
        
        if important_files:
            body_lines.append("📄 فایل‌های مهم:")
            body_lines.extend(important_files)
        
        return f"{title}\n\n" + "\n".join(body_lines)
    
    def push_changes(self, custom_message: str = "", dry_run: bool = False) -> bool:
        """ارسال تغییرات به گیت‌هاب"""
        print("🚀 شروع تحلیل تغییرات...")
        
        # تحلیل تغییرات
        changes = self._analyze_changes()
        
        if changes['total_files'] == 0:
            print("ℹ️ تغییری برای ارسال وجود ندارد.")
            return True
        
        print(f"📊 {changes['total_files']} فایل تغییر یافته")
        
        # تولید پیام کمیت
        commit_message = self._generate_commit_message(changes, custom_message)
        
        if dry_run:
            print("\n" + "="*50)
            print("🔍 پیش‌نمایش پیام کمیت:")
            print("="*50)
            print(commit_message)
            print("="*50)
            return True
        
        # مرحله‌بندی تغییرات
        print("📦 مرحله‌بندی تغییرات...")
        stdout, stderr, code = self._run_git_command(['git', 'add', '-A'])
        if code != 0:
            print(f"❌ خطا در مرحله‌بندی: {stderr}")
            return False
        
        # انجام کمیت
        print("💾 انجام کمیت...")
        stdout, stderr, code = self._run_git_command(['git', 'commit', '-m', commit_message])
        if code != 0:
            print(f"❌ خطا در کمیت: {stderr}")
            return False
        
        # پوش به ریموت
        print("📤 ارسال به گیت‌هاب...")
        stdout, stderr, code = self._run_git_command(['git', 'push', 'origin', self.branch])
        if code != 0:
            print(f"❌ خطا در پوش: {stderr}")
            return False
        
        print("✅ ارسال با موفقیت انجام شد!")
        print(f"🌿 شاخه: {self.branch}")
        print(f"📊 تغییرات: {self._generate_change_summary(changes)}")
        
        return True

def main():
    parser = argparse.ArgumentParser(description='اسکریپت پیشرفته ارسال خودکار به گیت‌هاب')
    parser.add_argument('--message', '-m', type=str, default='', help='پیام دلخواه برای کمیت')
    parser.add_argument('--auto', '-a', action='store_true', help='ارسال خودکار بدون پیام')
    parser.add_argument('--dry-run', '-d', action='store_true', help='فقط نمایش پیام کمیت بدون ارسال')
    
    args = parser.parse_args()
    
    git_push = SmartGitPush()
    
    if args.dry_run:
        success = git_push.push_changes(args.message, dry_run=True)
    else:
        success = git_push.push_changes(args.message, dry_run=False)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
