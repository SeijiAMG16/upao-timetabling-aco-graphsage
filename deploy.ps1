# Script de Despliegue Rápido
# ================================

Write-Host "🚀 DESPLIEGUE SISTEMA UPAO TIMETABLING" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que estemos en el directorio correcto
if (-not (Test-Path ".\DEPLOYMENT_GUIDE.md")) {
    Write-Host "❌ Error: Ejecuta este script desde la raíz del proyecto" -ForegroundColor Red
    exit 1
}

Write-Host "📦 Paso 1: Preparando archivos..." -ForegroundColor Yellow
Write-Host ""

# Verificar que existe el backup
$backupFiles = Get-ChildItem -Path "backend" -Filter "backup_upao_timetabling_*.sql" | Sort-Object LastWriteTime -Descending
if ($backupFiles.Count -eq 0) {
    Write-Host "❌ No se encontró backup de la base de datos" -ForegroundColor Red
    Write-Host "   Ejecuta: cd backend; python create_backup.py" -ForegroundColor Yellow
    exit 1
} else {
    $latestBackup = $backupFiles[0]
    Write-Host "✅ Backup encontrado: $($latestBackup.Name)" -ForegroundColor Green
    Write-Host "   Tamaño: $([math]::Round($latestBackup.Length / 1MB, 2)) MB" -ForegroundColor Gray
}

Write-Host ""
Write-Host "📋 Paso 2: Checklist Pre-Deployment" -ForegroundColor Yellow
Write-Host ""

$checks = @(
    @{Name="Git instalado"; Command="git --version"},
    @{Name="Node.js instalado"; Command="node --version"},
    @{Name="npm instalado"; Command="npm --version"},
    @{Name="Heroku CLI instalado"; Command="heroku --version"}
)

foreach ($check in $checks) {
    try {
        $null = Invoke-Expression $check.Command 2>&1
        Write-Host "  ✅ $($check.Name)" -ForegroundColor Green
    } catch {
        Write-Host "  ❌ $($check.Name)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "🔑 Paso 3: Información Necesaria" -ForegroundColor Yellow
Write-Host ""
Write-Host "Necesitarás tener a mano:" -ForegroundColor White
Write-Host "  1. Credenciales de Digital Ocean Database" -ForegroundColor Gray
Write-Host "  2. URL de tu backend en Digital Ocean (después de crearlo)" -ForegroundColor Gray
Write-Host "  3. Cuenta de Heroku configurada" -ForegroundColor Gray
Write-Host ""

Write-Host "📖 Paso 4: Siguiente Pasos" -ForegroundColor Yellow
Write-Host ""
Write-Host "Abre DEPLOYMENT_GUIDE.md y sigue las instrucciones:" -ForegroundColor White
Write-Host ""
Write-Host "  Orden recomendado:" -ForegroundColor Cyan
Write-Host "  1️⃣  Crear base de datos en Digital Ocean" -ForegroundColor White
Write-Host "  2️⃣  Restaurar backup (archivo: $($latestBackup.Name))" -ForegroundColor White
Write-Host "  3️⃣  Desplegar backend en Digital Ocean App Platform" -ForegroundColor White
Write-Host "  4️⃣  Desplegar frontend en Heroku" -ForegroundColor White
Write-Host "  5️⃣  Configurar variables de entorno" -ForegroundColor White
Write-Host "  6️⃣  Probar el sistema" -ForegroundColor White
Write-Host ""

$openGuide = Read-Host "¿Quieres abrir la guía de despliegue ahora? (s/n)"
if ($openGuide -eq "s" -or $openGuide -eq "S" -or $openGuide -eq "y" -or $openGuide -eq "Y") {
    Start-Process "DEPLOYMENT_GUIDE.md"
}

Write-Host ""
Write-Host "✨ ¡Listo! Sigue la guía paso a paso para desplegar el sistema." -ForegroundColor Green
Write-Host ""
