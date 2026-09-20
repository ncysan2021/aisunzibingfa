$content = Get-Clipboard -Raw
$content | Out-File -FilePath "C:\Users\san-20250514\aisunzibingfa\ricky-draft.md" -Encoding utf8 -NoNewline
Get-Item "C:\Users\san-20250514\aisunzibingfa\ricky-draft.md" | Select-Object Name, Length

Write-Host "`n=== 前 5 行 ===" -ForegroundColor Cyan
Get-Content "C:\Users\san-20250514\aisunzibingfa\ricky-draft.md" -TotalCount 5

Write-Host "`n=== 后 5 行 ===" -ForegroundColor Cyan
Get-Content "C:\Users\san-20250514\aisunzibingfa\ricky-draft.md" | Select-Object -Last 5