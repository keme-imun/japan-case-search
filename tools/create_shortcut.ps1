<#
바탕화면에 이 앱의 바로가기를 만든다 (아이콘 포함).

  # 1) 로컬 실행용 (run_app.bat 을 띄운다)
  powershell -ExecutionPolicy Bypass -File tools\create_shortcut.ps1

  # 2) 배포된 앱을 "앱 창"으로 여는 바로가기
  #    Chrome/Edge 의 --app 플래그를 쓰므로 주소창·탭 없이 열린다.
  powershell -ExecutionPolicy Bypass -File tools\create_shortcut.ps1 -Url "https://내앱.streamlit.app"
#>

param(
    [string]$Url = "",
    [ValidateSet("chrome", "edge")] [string]$Browser = "chrome",
    [string]$Name = "일본 판례 검색"
)

$ErrorActionPreference = "Stop"

$root    = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$icon    = Join-Path $root "assets\icon.ico"
$desktop = [Environment]::GetFolderPath("Desktop")

function Find-Browser([string]$which) {
    if ($which -eq "edge") {
        $candidates = @(
            "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
            "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
        )
    } else {
        $candidates = @(
            "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
            "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
            "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
        )
    }
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    return $null
}

if ($Url) {
    # 배포된 앱을 앱 창으로 여는 바로가기
    $exe = Find-Browser $Browser
    if (-not $exe) { throw "$Browser 를 찾을 수 없습니다. -Browser edge 로 다시 시도해 보세요." }
    $target    = $exe
    $arguments = "--app=$Url"
    $workdir   = Split-Path -Parent $exe
} else {
    # 로컬 실행용 바로가기
    $target = Join-Path $root "run_app.bat"
    if (-not (Test-Path $target)) { throw "run_app.bat 을 찾을 수 없습니다: $target" }
    $arguments = ""
    $workdir   = $root
}

$linkPath = Join-Path $desktop "$Name.lnk"
$shell = New-Object -ComObject WScript.Shell
$sc = $shell.CreateShortcut($linkPath)
$sc.TargetPath       = $target
$sc.Arguments        = $arguments
$sc.WorkingDirectory = $workdir
$sc.Description      = "일본 판례 검색 · 한국어 요약"
if (Test-Path $icon) { $sc.IconLocation = "$icon,0" }
$sc.Save()

Write-Output "바로가기를 만들었습니다: $linkPath"
if ($Url) { Write-Output "  대상: $target $arguments" }
else      { Write-Output "  대상: $target (로컬 실행)" }
