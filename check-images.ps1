# check-images.ps1
# 扫描 Hugo content/ 下所有图片引用，检查 alt / title / caption 是否齐全

param(
    [string]$ContentPath = ".\content",
    [string]$OutputCsv   = ".\image-audit.csv"
)

$results = @()

function New-Row {
    param($File, $Line, $Type, $Src, $Alt, $Title, $Caption)
    $missing = @()
    if (-not $Alt) { $missing += "alt" }
    if ($Type -ne "Cover" -and -not $Title) { $missing += "title" }
    if ($Type -eq "Figure" -and -not $Caption) { $missing += "caption" }
    [PSCustomObject]@{
        File     = $File
        Line     = $Line
        Type     = $Type
        Src      = $Src
        Alt      = $Alt
        Title    = $Title
        Caption  = $Caption
        Missing  = ($missing -join ",")
    }
}

Get-ChildItem -Path $ContentPath -Recurse -Filter *.md | ForEach-Object {
    $file = $_.FullName
    $lines = Get-Content $file

    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        $lineNo = $i + 1

        # Markdown 图片：![alt](src "title")
        $mdMatches = [regex]::Matches($line, '!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)')
        foreach ($m in $mdMatches) {
            $results += New-Row $file $lineNo "Markdown" `
                $m.Groups[2].Value $m.Groups[1].Value $m.Groups[3].Value ""
        }

        # Figure shortcode：{{< figure src="..." alt="..." title="..." caption="..." >}}
        $figMatches = [regex]::Matches($line, '\{\{<\s*figure\s+([^>]+)>\}\}')
        foreach ($m in $figMatches) {
            $attrs = $m.Groups[1].Value
            $src     = ([regex]::Match($attrs, 'src\s*=\s*"([^"]*)"')).Groups[1].Value
            $alt     = ([regex]::Match($attrs, 'alt\s*=\s*"([^"]*)"')).Groups[1].Value
            $title   = ([regex]::Match($attrs, 'title\s*=\s*"([^"]*)"')).Groups[1].Value
            $caption = ([regex]::Match($attrs, 'caption\s*=\s*"([^"]*)"')).Groups[1].Value
            $results += New-Row $file $lineNo "Figure" $src $alt $title $caption
        }

        # HTML img：<img src="..." alt="..." title="...">
        $imgMatches = [regex]::Matches($line, '<img\s+[^>]*>')
        foreach ($m in $imgMatches) {
            $tag = $m.Value
            $src   = ([regex]::Match($tag, 'src\s*=\s*"([^"]*)"')).Groups[1].Value
            $alt   = ([regex]::Match($tag, 'alt\s*=\s*"([^"]*)"')).Groups[1].Value
            $title = ([regex]::Match($tag, 'title\s*=\s*"([^"]*)"')).Groups[1].Value
            $results += New-Row $file $lineNo "HTML" $src $alt $title ""
        }
    }

    # Front Matter cover 字段
    $content = Get-Content $file -Raw
    $fmMatch = [regex]::Match($content, '(?s)^---\s*\r?\n(.*?)\r?\n---')
    if ($fmMatch.Success) {
        $fm = $fmMatch.Groups[1].Value
        $coverImage   = ([regex]::Match($fm, 'image\s*:\s*"?([^"\r\n]+)"?')).Groups[1].Value
        $coverAlt     = ([regex]::Match($fm, 'alt\s*:\s*"?([^"\r\n]+)"?')).Groups[1].Value
        $coverCaption = ([regex]::Match($fm, 'caption\s*:\s*"?([^"\r\n]+)"?')).Groups[1].Value
        if ($coverImage) {
            $results += New-Row $file "front-matter" "Cover" `
                $coverImage $coverAlt "" $coverCaption
        }
    }
}

$results | Export-Csv -Path $OutputCsv -NoTypeInformation -Encoding UTF8

Write-Host ""
Write-Host "共检查 $($results.Count) 处图片引用" -ForegroundColor Cyan
Write-Host ""

$missing = $results | Where-Object { $_.Missing -ne "" }
if ($missing.Count -eq 0) {
    Write-Host "所有图片 alt / title / caption 齐全" -ForegroundColor Green
} else {
    Write-Host "$($missing.Count) 处缺字段：" -ForegroundColor Yellow
    $missing | Format-Table File, Line, Type, Src, Missing -AutoSize
}

Write-Host ""
Write-Host "完整报告：$OutputCsv" -ForegroundColor Gray
