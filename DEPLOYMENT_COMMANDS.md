# COMANDOS RÁPIDOS PARA DEPLOYMENT

## 1. PREPARACIÓN LOCAL

### Instalar dependencia serve en frontend
```bash
cd frontend
npm install serve --save
npm install
cd ..
```

### Commit de todos los cambios
```bash
git add .
git commit -m "Preparado para deployment en Digital Ocean y Heroku"
git push origin main
```

## 2. DIGITAL OCEAN - BASE DE DATOS

### Crear desde Web UI:
- Databases → Create Database Cluster
- MySQL 8, Basic plan ($15/mes)
- Datacenter: New York 3
- Download CA Certificate

### Restaurar Backup (desde tu máquina local):
```bash
mysql -h your-db-host.db.ondigitalocean.com -P 25060 -u doadmin -p --ssl-mode=REQUIRED < backend\backup_upao_timetabling_20251201_185228.sql
```

### Verificar:
```bash
mysql -h your-db-host.db.ondigitalocean.com -P 25060 -u doadmin -p --ssl-mode=REQUIRED
USE upao_timetabling;
SHOW TABLES;
SELECT COUNT(*) FROM course_sections;
```

## 3. DIGITAL OCEAN - BACKEND (App Platform)

### Crear desde Web UI:
- Apps → Create App
- Connect GitHub repository
- Source: /backend
- Environment Variables:
  ```
  DATABASE_URL=mysql+pymysql://doadmin:PASSWORD@HOST:25060/upao_timetabling?charset=utf8mb4
  SECRET_KEY=cambiar-esto-por-algo-seguro-y-aleatorio-123456789
  ENVIRONMENT=production
  CORS_ORIGINS=http://localhost:5173,https://tu-frontend.herokuapp.com
  FRONTEND_URL=https://tu-frontend.herokuapp.com
  ```

### Configuración App Spec:
```yaml
name: upao-timetabling-backend
services:
- name: backend
  source_dir: /backend
  environment_slug: python
  run_command: uvicorn app.main:app --host 0.0.0.0 --port 8080
  http_port: 8080
  instance_count: 1
  instance_size_slug: basic-xxs
```

### Probar backend:
```bash
curl https://tu-app.ondigitalocean.app/
curl https://tu-app.ondigitalocean.app/health
```

## 4. HEROKU - FRONTEND

### Instalar Heroku CLI (si no lo tienes):
```bash
# Windows: Descargar de https://devcenter.heroku.com/articles/heroku-cli
# O con chocolatey:
choco install heroku-cli
```

### Login y crear app:
```bash
heroku login
heroku create upao-timetabling-frontend
```

### Configurar variable de entorno:
```bash
# Reemplaza con tu URL real de Digital Ocean
heroku config:set VITE_API_URL=https://tu-app.ondigitalocean.app -a upao-timetabling-frontend
```

### Desplegar (Opción 1 - Recomendada):
```bash
cd frontend
git init
git add .
git commit -m "Deploy to Heroku"
heroku git:remote -a upao-timetabling-frontend
git push heroku main
```

### Desplegar (Opción 2 - Git Subtree desde raíz):
```bash
# Desde la raíz del proyecto
git subtree push --prefix frontend heroku main
```

### Ver logs:
```bash
heroku logs --tail -a upao-timetabling-frontend
```

### Abrir app:
```bash
heroku open -a upao-timetabling-frontend
```

## 5. ACTUALIZAR CORS EN BACKEND

Una vez que tengas las URLs finales, actualiza en Digital Ocean:

```
CORS_ORIGINS=https://upao-timetabling-frontend.herokuapp.com,https://tu-backend.ondigitalocean.app
```

## 6. VERIFICACIÓN FINAL

### Test Backend:
```bash
# Health check
curl https://tu-backend.ondigitalocean.app/health

# Docs
https://tu-backend.ondigitalocean.app/docs
```

### Test Frontend:
1. Abrir: https://upao-timetabling-frontend.herokuapp.com
2. Login: admin / admin123
3. Ir a "Generar Horario"
4. Click "Generar Horario Completo"
5. Esperar 3-5 minutos
6. Verificar descarga de Excel

## 7. TROUBLESHOOTING

### Backend no conecta a BD:
```bash
# Verificar desde Digital Ocean Console
# Apps → tu-app → Console
python
>>> from app.database import engine
>>> print(engine.url)
>>> engine.connect()
```

### Frontend no carga:
```bash
heroku logs --tail -a upao-timetabling-frontend
# Buscar errores de build o runtime
```

### CORS Error:
```bash
# Verificar en Digital Ocean:
# Apps → tu-app → Settings → Environment Variables
# CORS_ORIGINS debe incluir ambas URLs (frontend y backend)
```

### Rebuild Frontend:
```bash
heroku repo:purge_cache -a upao-timetabling-frontend
git commit --allow-empty -m "Rebuild"
git push heroku main
```

## 8. COMANDOS ÚTILES

### Ver status Heroku:
```bash
heroku ps -a upao-timetabling-frontend
heroku logs --tail -a upao-timetabling-frontend
```

### Restart app:
```bash
heroku restart -a upao-timetabling-frontend
```

### Ver variables de entorno:
```bash
heroku config -a upao-timetabling-frontend
```

### Agregar dominio custom (opcional):
```bash
heroku domains:add www.tudominio.com -a upao-timetabling-frontend
```

## 9. COSTOS MENSUALES

- Digital Ocean Database (Basic): $15
- Digital Ocean App (Basic XXS): $5
- Heroku Eco Dyno: $5
**TOTAL: $25/mes**

## 10. MANTENIMIENTO

### Actualizar código:
```bash
# Backend (automático desde GitHub)
git push origin main
# Digital Ocean rebuildeará automáticamente

# Frontend
cd frontend
git add .
git commit -m "Update"
git push heroku main
```

### Backup base de datos:
```bash
# Programar backup automático en Digital Ocean
# Dashboard → Databases → tu-db → Settings → Backups
# Configurar: Daily backups
```

### Monitoreo:
- Digital Ocean: Apps → Insights (CPU, RAM, Requests)
- Heroku: Metrics tab en dashboard
