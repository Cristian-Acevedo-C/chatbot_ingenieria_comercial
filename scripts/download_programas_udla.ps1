[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$base = "$HOME\Proyectos\chatbot_ingenieria_comercial"
$mapaPath = Join-Path $base "data\mapa_links_ramos.csv"
$docsBase = Join-Path $base "documentos"
$logPath = Join-Path $base "data\descarga_programas_log.csv"

function Limpiar-Nombre {
    param([string]$Texto)

    $texto = $Texto.ToLower()
    $texto = $texto -replace "á","a"
    $texto = $texto -replace "é","e"
    $texto = $texto -replace "í","i"
    $texto = $texto -replace "ó","o"
    $texto = $texto -replace "ú","u"
    $texto = $texto -replace "ñ","n"
    $texto = $texto -replace "[^a-z0-9]+","_"
    $texto = $texto -replace "^_+|_+$",""

    if ([string]::IsNullOrWhiteSpace($texto)) {
        return "sin_nombre"
    }

    return $texto
}

function Es-Pdf-Valido {
    param([string]$Path)

    if (!(Test-Path $Path)) {
        return $false
    }

    if ((Get-Item $Path).Length -lt 1000) {
        return $false
    }

    $bytes = [System.IO.File]::ReadAllBytes($Path)

    if ($bytes.Length -lt 4) {
        return $false
    }

    $header = [System.Text.Encoding]::ASCII.GetString($bytes[0..3])
    return $header -eq "%PDF"
}

$mapa = Import-Csv $mapaPath

$years = 2026..2015
$periods = @("103","102","101")

$prefixes = foreach ($y in $years) {
    foreach ($p in $periods) {
        "$y$p"
    }
}

$resultados = @()

foreach ($r in $mapa) {
    $codigo = $r.codigo.Trim()
    $nombre = $r.nombre.Trim()
    $semestre = [int]$r.semestre
    $sem = "{0:D2}" -f $semestre
    $slug = Limpiar-Nombre $nombre

    $carpeta = Join-Path $docsBase "semestre_$sem"
    New-Item -ItemType Directory -Force -Path $carpeta | Out-Null

    $destinoFinal = Join-Path $carpeta "${sem}_${codigo}_${slug}.pdf"

    if (Test-Path $destinoFinal) {
        Write-Host "Ya existe: $codigo - $nombre" -ForegroundColor DarkGray

        $resultados += [pscustomobject]@{
            codigo = $codigo
            nombre = $nombre
            semestre = $semestre
            estado = "ya_existia"
            url = ""
            archivo = $destinoFinal
        }

        continue
    }

    $encontrado = $false

    foreach ($prefix in $prefixes) {
        $url = "https://programas.udla.cl/$prefix$codigo.pdf"
        $tmp = Join-Path $env:TEMP "$prefix$codigo.pdf"

        try {
            Invoke-WebRequest -Uri $url -OutFile $tmp -TimeoutSec 15 -UseBasicParsing -ErrorAction Stop

            if (Es-Pdf-Valido $tmp) {
                Copy-Item $tmp $destinoFinal -Force
                Remove-Item $tmp -Force -ErrorAction SilentlyContinue

                Write-Host "OK: $codigo - $nombre" -ForegroundColor Green

                $resultados += [pscustomobject]@{
                    codigo = $codigo
                    nombre = $nombre
                    semestre = $semestre
                    estado = "descargado"
                    url = $url
                    archivo = $destinoFinal
                }

                $encontrado = $true
                break
            }
        } catch {
        }

        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 150
    }

    if (-not $encontrado) {
        Write-Host "NO ENCONTRADO: $codigo - $nombre" -ForegroundColor Yellow

        $resultados += [pscustomobject]@{
            codigo = $codigo
            nombre = $nombre
            semestre = $semestre
            estado = "no_encontrado"
            url = ""
            archivo = ""
        }
    }
}

$resultados | Export-Csv $logPath -NoTypeInformation -Encoding UTF8

Write-Host ""
Write-Host "Proceso terminado." -ForegroundColor Cyan
Write-Host "Log guardado en: $logPath" -ForegroundColor Cyan

$descargados = ($resultados | Where-Object { $_.estado -eq "descargado" }).Count
$existian = ($resultados | Where-Object { $_.estado -eq "ya_existia" }).Count
$no = ($resultados | Where-Object { $_.estado -eq "no_encontrado" }).Count

Write-Host "Descargados: $descargados"
Write-Host "Ya existían: $existian"
Write-Host "No encontrados: $no"
