# اسکریپت بررسی و آماده‌سازی Docker قبل از اجرا
# این اسکریپت تمام پیش‌نیازها را بررسی می‌کند

param(
    [switch]$Fix = $false
)

Write-Host "`n🔍 بررسی تنظیمات Docker..." -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

$errors = @()
$warnings = @()

# بررسی 1: وجود Docker
Write-Host "`n[1] بررسی نصب Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Docker نصب شده است: $dockerVersion" -ForegroundColor Green
    }
    else {
        $errors += "Docker نصب نشده است. لطفاً Docker Desktop را نصب کنید."
    }
}
catch {
    $errors += "Docker پیدا نشد. لطفاً Docker Desktop را نصب کنید."
}

# بررسی 2: Docker در حال اجرا است
Write-Host "`n[2] بررسی وضعیت Docker..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Docker در حال اجرا است" -ForegroundColor Green
    }
    else {
        $errors += "Docker در حال اجرا نیست. لطفاً Docker Desktop را اجرا کنید."
    }
}
catch {
    $errors += "نمی‌توان به Docker متصل شد. لطفاً Docker Desktop را اجرا کنید."
}

# بررسی 3: فایل‌های Secrets
Write-Host "`n[3] بررسی فایل‌های Secrets..." -ForegroundColor Yellow
$secretsDir = Join-Path $projectRoot "secrets"
$requiredSecrets = @(
    @{Name = "db_password.txt"; Description = "رمز دیتابیس" },
    @{Name = "redis_password.txt"; Description = "رمز Redis" },
    @{Name = "django_secret_key.txt"; Description = "کلید مخفی Django" }
)

if (-not (Test-Path $secretsDir)) {
    New-Item -ItemType Directory -Path $secretsDir -Force | Out-Null
    Write-Host "  📁 پوشه secrets ایجاد شد" -ForegroundColor Yellow
}

$missingSecrets = @()
foreach ($secret in $requiredSecrets) {
    $secretPath = Join-Path $secretsDir $secret.Name
    if (Test-Path $secretPath) {
        $content = Get-Content $secretPath -Raw
        if ([string]::IsNullOrWhiteSpace($content)) {
            $warnings += "فایل $($secret.Name) خالی است"
            Write-Host "  ⚠ فایل $($secret.Name) خالی است" -ForegroundColor Yellow
        }
        else {
            Write-Host "  ✅ $($secret.Name) موجود است" -ForegroundColor Green
        }
    }
    else {
        $missingSecrets += $secret
        Write-Host "  ❌ $($secret.Name) پیدا نشد" -ForegroundColor Red
    }
}

if ($missingSecrets.Count -gt 0) {
    if ($Fix) {
        Write-Host "`n🔧 ایجاد فایل‌های Secrets..." -ForegroundColor Yellow
        & "$scriptPath\setup-secrets.ps1"
    }
    else {
        $errors += "فایل‌های Secrets پیدا نشدند. اجرا کنید: .\docker-scripts\setup-secrets.ps1"
    }
}

# بررسی 4: فایل .env
Write-Host "`n[4] بررسی فایل .env..." -ForegroundColor Yellow
$envFile = Join-Path $projectRoot ".env"
$envExample = Join-Path $projectRoot "env.example"

if (Test-Path $envFile) {
    Write-Host "  ✅ فایل .env موجود است" -ForegroundColor Green
}
else {
    if (Test-Path $envExample) {
        if ($Fix) {
            Copy-Item $envExample $envFile
            Write-Host "  ✅ فایل .env از env.example ایجاد شد" -ForegroundColor Green
            $warnings += "لطفاً فایل .env را تنظیم کنید"
        }
        else {
            $warnings += "فایل .env موجود نیست. می‌توانید از env.example کپی کنید: Copy-Item env.example .env"
        }
    }
    else {
        $warnings += "فایل env.example پیدا نشد"
    }
}

# بررسی 5: فایل‌های Docker
Write-Host "`n[5] بررسی فایل‌های Docker..." -ForegroundColor Yellow
$dockerFiles = @(
    @{Path = "Dockerfile"; Description = "Dockerfile اصلی" },
    @{Path = "docker-compose.yml"; Description = "docker-compose.yml" },
    @{Path = "docker/entrypoint.sh"; Description = "اسکریپت entrypoint" },
    @{Path = "docker/healthcheck.sh"; Description = "اسکریپت healthcheck" }
)

foreach ($file in $dockerFiles) {
    $filePath = Join-Path $projectRoot $file.Path
    if (Test-Path $filePath) {
        Write-Host "  ✅ $($file.Description) موجود است" -ForegroundColor Green
    }
    else {
        $errors += "$($file.Description) پیدا نشد: $($file.Path)"
        Write-Host "  ❌ $($file.Description) پیدا نشد" -ForegroundColor Red
    }
}

# بررسی 6: requirements.txt
Write-Host "`n[6] بررسی requirements.txt..." -ForegroundColor Yellow
$requirementsFile = Join-Path $projectRoot "requirements.txt"
if (Test-Path $requirementsFile) {
    Write-Host "  ✅ requirements.txt موجود است" -ForegroundColor Green
}
else {
    $errors += "requirements.txt پیدا نشد"
    Write-Host "  ❌ requirements.txt پیدا نشد" -ForegroundColor Red
}

# بررسی 7: پورت‌های استفاده شده
Write-Host "`n[7] بررسی پورت‌های استفاده شده..." -ForegroundColor Yellow
$ports = @(3307, 6379, 8000, 8080, 443)
$usedPorts = @()

foreach ($port in $ports) {
    $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connection) {
        $usedPorts += $port
        Write-Host "  ⚠ پورت $port در حال استفاده است" -ForegroundColor Yellow
    }
    else {
        Write-Host "  ✅ پورت $port آزاد است" -ForegroundColor Green
    }
}

if ($usedPorts.Count -gt 0) {
    $warnings += "پورت‌های زیر در حال استفاده هستند: $($usedPorts -join ', '). ممکن است نیاز به تغییر در docker-compose.yml باشد."
}

# نمایش نتایج
Write-Host "`n" + ("=" * 50) -ForegroundColor Cyan
Write-Host "📊 خلاصه بررسی" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan

if ($errors.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "`n✅ همه چیز آماده است! می‌توانید Docker را اجرا کنید:" -ForegroundColor Green
    Write-Host "  docker compose up -d --build" -ForegroundColor Cyan
    exit 0
}
else {
    if ($errors.Count -gt 0) {
        Write-Host "`n❌ خطاها:" -ForegroundColor Red
        foreach ($error in $errors) {
            Write-Host "  - $error" -ForegroundColor Red
        }
    }

    if ($warnings.Count -gt 0) {
        Write-Host "`n⚠ هشدارها:" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "  - $warning" -ForegroundColor Yellow
        }
    }

    if ($errors.Count -gt 0) {
        Write-Host "`n💡 برای رفع خطاها، اسکریپت را با پارامتر -Fix اجرا کنید:" -ForegroundColor Yellow
        Write-Host "  .\docker-scripts\check-docker-setup.ps1 -Fix" -ForegroundColor Cyan
        exit 1
    }
    else {
        Write-Host "`n💡 می‌توانید با هشدارها ادامه دهید یا آن‌ها را برطرف کنید." -ForegroundColor Yellow
        exit 0
    }
}

