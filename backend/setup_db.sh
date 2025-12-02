#!/bin/bash

# Script para configurar base de datos en Digital Ocean
# Ejecutar después de crear el Managed Database PostgreSQL

echo "🔧 Configuración de Base de Datos en Digital Ocean"
echo "=================================================="
echo ""
echo "Este script te ayudará a configurar la base de datos."
echo ""

# Variables (reemplazar con tus valores)
read -p "Ingresa el HOST de la BD (ej: db-mysql-nyc3-12345-do-user-123456-0.b.db.ondigitalocean.com): " DB_HOST
read -p "Ingresa el PUERTO (default 25060): " DB_PORT
DB_PORT=${DB_PORT:-25060}
read -p "Ingresa el USUARIO (default doadmin): " DB_USER
DB_USER=${DB_USER:-doadmin}
read -sp "Ingresa la CONTRASEÑA: " DB_PASSWORD
echo ""
read -p "Ingresa el NOMBRE DE LA BD (default defaultdb): " DB_NAME
DB_NAME=${DB_NAME:-defaultdb}

echo ""
echo "📦 Restaurando backup..."

# Restaurar backup
mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASSWORD --ssl-mode=REQUIRED < backup_upao_timetabling_*.sql

if [ $? -eq 0 ]; then
    echo "✅ Backup restaurado exitosamente!"
    echo ""
    echo "🔗 Cadena de conexión para .env:"
    echo "DATABASE_URL=mysql+pymysql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/upao_timetabling?ssl_ca=/path/to/ca-certificate.crt"
else
    echo "❌ Error al restaurar backup"
    exit 1
fi
