# PersonalNotebook Windows Build
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot/../app/personal_notebook_app"
Write-Host "=== Flutter Windows Build ==="
flutter clean
flutter pub get
flutter analyze
flutter test
flutter build windows --release
Write-Host "✅ Windows build complete"
Write-Host "Installer: app/personal_notebook_app/build/windows/x64/runner/Release/"
