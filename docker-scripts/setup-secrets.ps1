param(
    [string]$OutputDirectory = "secrets",
    [switch]$Force
)

Write-Host "=== ایجاد/به‌روزرسانی فایل‌های Secrets Docker ===" -ForegroundColor Green

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

if (!(Test-Path $OutputDirectory)) {
    New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
    Write-Host "✓ پوشه $OutputDirectory ایجاد شد" -ForegroundColor Green
}

function Get-EnvValueFromFile {
    param([string]$Key)

    if (!(Test-Path ".env")) {
        return $null
    }

    try {
        $regex = "^\s*{0}\s*=\s*(.+)$" -f [regex]::Escape($Key)
        $match = Select-String -Path ".env" -Pattern $regex -SimpleMatch | Select-Object -First 1
        if ($null -ne $match) {
            $value = $match.Matches[0].Groups[1].Value.Trim()
            return $value.Trim("'`"").Trim()
        }
    }
    catch {
        Write-Host "⚠ خطا در خواندن مقدار $Key از فایل .env" -ForegroundColor Yellow
    }
    return $null
}

function Read-SecretValue {
    param(
        [string]$Prompt,
        [string]$DefaultValue
    )

    if ([string]::IsNullOrWhiteSpace($DefaultValue)) {
        return Read-Host -AsSecureString $Prompt | `
            ForEach-Object { (New-Object System.Net.NetworkCredential("", $_)).Password }
    }
    else {
        $useExisting = Read-Host "$Prompt (مقدار فعلی پیدا شد. استفاده شود؟ y/N)"
        if ($useExisting -eq "y" -or $useExisting -eq "Y") {
            return $DefaultValue
        }
        return Read-Host -AsSecureString $Prompt | `
            ForEach-Object { (New-Object System.Net.NetworkCredential("", $_)).Password }
    }
}

$secrets = @(
    @{ Name = "SECRET_KEY"; Prompt = "مقدار SECRET_KEY جنگو"; FileName = "django_secret_key.txt"; EnvKey = "SECRET_KEY" },
    @{ Name = "DB_PASSWORD"; Prompt = "رمز دیتابیس"; FileName = "db_password.txt"; EnvKey = "DB_PASSWORD" },
    @{ Name = "REDIS_PASSWORD"; Prompt = "رمز Redis"; FileName = "redis_password.txt"; EnvKey = "REDIS_PASSWORD" }
)

foreach ($secret in $secrets) {
    $filePath = Join-Path $OutputDirectory $secret.FileName
    $existingValue = ""

    if ((Test-Path $filePath) -and -not $Force) {
        $existingValue = Get-Content $filePath -Raw
    }

    $envFallback = Get-EnvValueFromFile -Key $secret.EnvKey

    if ($Force -and [string]::IsNullOrWhiteSpace($existingValue) -and -not [string]::IsNullOrWhiteSpace($envFallback)) {
        $value = $envFallback
        Write-Host "✓ مقدار $($secret.Name) از فایل .env خوانده شد" -ForegroundColor Green
    }
    else {
        $defaultValue = if (-not [string]::IsNullOrWhiteSpace($existingValue)) { $existingValue } elseif (-not [string]::IsNullOrWhiteSpace($envFallback)) { $envFallback } else { "" }
        $value = Read-SecretValue -Prompt $secret.Prompt -DefaultValue $defaultValue
    }

    if ([string]::IsNullOrWhiteSpace($value)) {
        Write-Host "⚠ مقدار برای $($secret.Name) خالی بود. عبور..." -ForegroundColor Yellow
        continue
    }

    Set-Content -Path $filePath -Value $value -NoNewline
    Write-Host "✓ فایل $filePath به‌روزرسانی شد" -ForegroundColor Green
}

Write-Host "`n🎉 فایل‌های Secrets آماده هستند. مطمئن شوید که در کنترل نسخه کامیت نشوند." -ForegroundColor Green

