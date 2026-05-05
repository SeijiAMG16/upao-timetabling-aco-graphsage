#!/bin/bash

# Script de despliegue automatizado para el Droplet de Digital Ocean
# Uso: ./deploy_server.sh

echo "🚀 Iniciando despliegue de UPAO Timetabling System..."

# 1. Obtener los últimos cambios
echo "📥 Actualizando repositorio..."
git pull origin main

# 2. Verificar archivo .env
if [ ! -f "backend/.env" ]; then
    echo "⚠️  No se encontró el archivo backend/.env"
    echo "🔧 Creando uno a partir del .env.example..."
    cp backend/.env.example backend/.env
    echo "❗ Por favor, edita backend/.env con tus credenciales de producción antes de continuar."
    exit 1
fi

# 3. Limpiar contenedores previos si existen (para evitar errores de ContainerConfig)
echo "🧹 Limpiando instalaciones previas..."
docker compose -f docker-compose.backend.yml down --remove-orphans 2>/dev/null || true

# 4. Levantar contenedores
echo "🐳 Construyendo y levantando contenedores con Docker Compose V2..."
docker compose -f docker-compose.backend.yml up -d --build

# 5. Verificar estado
echo "📊 Estado de los contenedores:"
docker compose -f docker-compose.backend.yml ps

echo "✅ Despliegue completado!"
echo "📺 Puedes ver los logs con: docker compose -f docker-compose.backend.yml logs -f backend"
