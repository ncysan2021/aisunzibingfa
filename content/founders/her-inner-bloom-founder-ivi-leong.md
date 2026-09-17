cd C:\Users\san-20250514\aisunzibingfa

$fileName   = "her-inner-bloom-founder-ivi-leong.md"
$targetDir  = "content\founders"          # 如果文章放根目录，改成 "."
$targetPath = Join-Path $targetDir $fileName
$branch     = "main"                      # 如果分支是 master，改成 "master"

# 确保目录存在
if (!(Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }

# 从剪贴板保存为 UTF-8 无 BOM
$content = Get-Clipboard -Raw
[System.IO.File]::WriteAllText((Join-Path (Get-Location) $targetPath), $content, [System.Text.UTF8Encoding]::new($false))

Write-Host "已保存: $targetPath" -ForegroundColor Green

# Git add / commit / push
git add $targetPath

if (git status --porcelain $targetPath) {
    git commit -m "Add article: Her Inner Bloom 创办人 Ivi Leong"
    git push origin $branch
    Write-Host "已提交并推送。Cloudflare Pages 会自动部署。" -ForegroundColor Green
} else {
    Write-Host "文件没有变更，跳过 commit / push。" -ForegroundColor Yellow
}