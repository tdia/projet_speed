$f = 'C:\Users\Tidiane\Documents\Gomycode\projet_speed\checkpoint_ReconnaissanceVocale_v2.py'
$lines = Get-Content $f -Encoding UTF8
$newLines = $lines[0..403] + $lines[409..($lines.Length-1)]
$newLines | Set-Content $f -Encoding UTF8
