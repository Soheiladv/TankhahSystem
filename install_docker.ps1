# PowerShell script to install Docker Desktop on Windows
# Run as Administrator

Write-Host "🐳 Installing Docker Desktop for Windows..." -ForegroundColor Green

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ This script requires Administrator privileges. Please run as Administrator." -ForegroundColor Red
    exit 1
}

# Enable WSL2 feature
Write-Host "🔧 Enabling WSL2 feature..." -ForegroundColor Yellow
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Download Docker Desktop
$dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
$dockerInstaller = "$env:TEMP\DockerDesktopInstaller.exe"

Write-Host "📥 Downloading Docker Desktop..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerInstaller
    Write-Host "✅ Docker Desktop downloaded successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to download Docker Desktop: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Install Docker Desktop
Write-Host "🚀 Installing Docker Desktop..." -ForegroundColor Yellow
try {
    Start-Process -FilePath $dockerInstaller -ArgumentList "install", "--quiet" -Wait
    Write-Host "✅ Docker Desktop installed successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to install Docker Desktop: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Clean up
Remove-Item $dockerInstaller -Force

Write-Host "🎉 Docker Desktop installation completed!" -ForegroundColor Green
Write-Host "⚠️  Please restart your computer and then run Docker Desktop." -ForegroundColor Yellow
Write-Host "📋 After restart, run: docker --version" -ForegroundColor Cyan
