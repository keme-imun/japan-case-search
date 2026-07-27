# 바탕화면에 이 앱의 바로가기를 만든다 (아이콘 포함).
#   powershell -ExecutionPolicy Bypass -File tools\create_shortcut.ps1

$ErrorActionPreference = "Stop"

$root     = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$target   = Join-Path $root "run_app.bat"
$icon     = Join-Path $root "assets\icon.ico"
$desktop  = [Environment]::GetFolderPath("Desktop")
$linkPath = Join-Path $desktop "일본 판례 검색.lnk"

if (-not (Test-Path $target)) { throw "run_app.bat 을 찾을 수 없습니다: $target" }

$shell = New-Object -ComObject WScript.Shell
$sc = $shell.CreateShortcut($linkPath)
$sc.TargetPath       = $target
$sc.WorkingDirectory = $root
$sc.Description      = "일본 판례 검색 · 한국어 요약"
if (Test-Path $icon) { $sc.IconLocation = "$icon,0" }
$sc.Save()

Write-Output "바로가기를 만들었습니다: $linkPath"
