$map = @{
    'Esportes e Aventura'         = 'Sports & Outdoors'
    'Informatica'                 = 'Computers & Tech'
    'Casa e Cozinha'              = 'Home & Kitchen'
    'Celulares e Telefonia'       = 'Cell Phones & Accessories'
    'Eletronicos'                 = 'Electronics'
    'Higiene e Cuidados Pessoais' = 'Personal Care'
    'Eletrodomesticos'            = 'Home Appliances'
    'Ferramentas e Construcao'    = 'Tools & Hardware'
    'Automotivo'                  = 'Automotive'
    'Saude e Beleza'              = 'Health & Beauty'
    'Moveis'                      = 'Furniture'
}

$articlesPath = 'C:\projetos\official-amazon-reviews\articles'
$dirs = Get-ChildItem $articlesPath -Directory
$fixed = 0; $errors = 0

foreach ($dir in $dirs) {
    $file = Join-Path $dir.FullName 'index.html'
    if (-not (Test-Path $file)) { continue }
    try {
        $content = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        $original = $content

        # Fix encoding quebrado
        $content = $content.Replace('â€"', '--')
        $content = $content.Replace('â€™', "'")
        $content = $content.Replace('Ã§', 'c')
        $content = $content.Replace('Ã£', 'a')
        $content = $content.Replace('Ã¢', 'a')

        # Fix categorias PT -> EN
        foreach ($pt in $map.Keys) {
            $content = $content.Replace($pt, $map[$pt])
        }

        if ($content -ne $original) {
            [System.IO.File]::WriteAllText($file, $content, [System.Text.Encoding]::UTF8)
            $fixed++
        }
    } catch {
        $errors++
        Write-Output "ERRO: $($dir.Name) — $_"
    }
}

Write-Output "Arquivos corrigidos: $fixed"
Write-Output "Erros: $errors"
