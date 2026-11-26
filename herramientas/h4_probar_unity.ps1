# H4 (prueba): monta un proyecto Unity vacio con la exportacion y ejecuta las comprobaciones.
# No toca Qazrix. Requisito: haber ejecutado antes herramientas/h4_exportar_unity.py.
# Uso (desde la raiz del proyecto):  powershell -File herramientas/h4_probar_unity.ps1
param(
    [string]$Unity = "E:\Utilities\Unity\6000.3.6f1\Editor\Unity.exe",
    [string]$Proyecto = "$env:USERPROFILE\CaceresDigital_PruebaUnity"
)
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$salida = Join-Path $raiz "renders\h4_unity"
if (Test-Path (Join-Path $Proyecto "Temp\UnityLockfile")) { throw "El proyecto de prueba esta abierto en Unity: cierralo." }

foreach ($c in "Assets\SantaMaria\Texturas", "Assets\Editor", "Packages", "ProjectSettings") {
    New-Item -ItemType Directory -Force (Join-Path $Proyecto $c) | Out-Null
}
Copy-Item "$raiz\exports\unity\santa_maria.fbx", "$raiz\exports\unity\manifiesto.json" "$Proyecto\Assets\SantaMaria\" -Force
Copy-Item "$raiz\exports\unity\Texturas\*.png" "$Proyecto\Assets\SantaMaria\Texturas\" -Force
Copy-Item "$PSScriptRoot\unity\PruebaSantaMaria.cs" "$Proyecto\Assets\Editor\" -Force
$paquetes = "$Proyecto\Packages\manifest.json"
if (-not (Test-Path $paquetes)) {
    $json = @'
{
  "dependencies": {
    "com.unity.render-pipelines.universal": "17.3.0",
    "com.unity.modules.imageconversion": "1.0.0",
    "com.unity.modules.imgui": "1.0.0",
    "com.unity.modules.jsonserialize": "1.0.0",
    "com.unity.modules.physics": "1.0.0",
    "com.unity.modules.ui": "1.0.0",
    "com.unity.modules.uielements": "1.0.0"
  }
}
'@
    [IO.File]::WriteAllText($paquetes, $json)
    [IO.File]::WriteAllText("$Proyecto\ProjectSettings\ProjectVersion.txt", "m_EditorVersion: 6000.3.6f1`n")
}

New-Item -ItemType Directory -Force $salida | Out-Null
Remove-Item "$salida\informe_unity.txt" -ErrorAction SilentlyContinue
$env:SANTAMARIA_SALIDA = $salida
$registro = Join-Path $Proyecto "prueba_unity.log"
# Sin -nographics: las capturas necesitan la tarjeta grafica.
$p = Start-Process -FilePath $Unity -PassThru -ArgumentList @(
    "-batchmode", "-projectPath", "`"$Proyecto`"", "-executeMethod", "PruebaSantaMaria.Ejecutar",
    "-logFile", "`"$registro`"")
$null = $p.Handle
if (-not $p.WaitForExit(900000)) { $p.Kill(); throw "Unity no termino en 15 minutos. Registro: $registro" }
"Unity termino con codigo $($p.ExitCode). Registro: $registro"
if (Test-Path "$salida\informe_unity.txt") { Get-Content "$salida\informe_unity.txt" -Encoding UTF8 }
else { Get-Content $registro -Tail 60 }
