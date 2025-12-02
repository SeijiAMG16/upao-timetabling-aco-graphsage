# Guía de Despliegue - Sistema de Horarios UPAO

## 📋 Requisitos Previos

1. Cuenta en Digital Ocean
2. Cuenta en Heroku
3. Git instalado
4. Heroku CLI instalado
5. Backup de la base de datos (`backup_upao_timetabling_*.sql`)

---

## 🗄️ Parte 1: Base de Datos en Digital Ocean

### 1.1. Crear Managed Database MySQL

1. Ingresa a Digital Ocean Dashboard
2. Ve a **Databases** → **Create Database Cluster**
3. Selecciona:
   - **Engine**: MySQL 8
   - **Plan**: Basic ($15/mes recomendado)
   - **Datacenter**: New York 3 (o el más cercano)
   - **Database name**: `upao-timetabling-db`

4. Espera 3-5 minutos a que se cree el cluster

### 1.2. Descargar CA Certificate

1. En el dashboard de tu database, ve a **Connection Details**
2. Descarga el **CA Certificate** (archivo `.crt`)
3. Guárdalo en un lugar seguro

### 1.3. Restaurar Backup

**Opción A: Desde tu máquina local**

```bash
# Navega a la carpeta del backup
cd "C:\Users\amaya\Downloads\10mo Ciclo\TESIS\upao-timetabling-aco-graphsage\backend"

# Restaura el backup (reemplaza con tus credenciales)
mysql -h your-db-host.db.ondigitalocean.com -P 25060 -u doadmin -p --ssl-mode=REQUIRED < backup_upao_timetabling_20251201_185228.sql
```

**Opción B: Desde Digital Ocean Droplet**

1. Crea un Droplet temporal Ubuntu
2. Instala MySQL client: `sudo apt install mysql-client`
3. Sube el backup con SCP
4. Ejecuta el comando de restauración

### 1.4. Verificar Restauración

```bash
mysql -h your-db-host.db.ondigitalocean.com -P 25060 -u doadmin -p --ssl-mode=REQUIRED

USE upao_timetabling;
SHOW TABLES;
SELECT COUNT(*) FROM course_sections;
```

### 1.5. Obtener Cadena de Conexión

Formato:
```
mysql+pymysql://doadmin:PASSWORD@HOST:25060/upao_timetabling?charset=utf8mb4
```

Ejemplo:
```
mysql+pymysql://doadmin:abc123xyz@db-mysql-nyc3-12345.db.ondigitalocean.com:25060/upao_timetabling?charset=utf8mb4
```

---

## 🚀 Parte 2: Backend en Digital Ocean App Platform

### 2.1. Preparar Repositorio

```bash
cd "C:\Users\amaya\Downloads\10mo Ciclo\TESIS\upao-timetabling-aco-graphsage"

# Asegurarse de que todo esté commiteado
git add .
git commit -m "Preparando para deployment"
git push origin main
```

### 2.2. Crear App en Digital Ocean

1. Ve a **Apps** → **Create App**
2. Conecta tu repositorio GitHub
3. Selecciona el repositorio `upao-timetabling-aco-graphsage`
4. Configuración:
   - **Source Directory**: `/backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Run Command**: `uvicorn app.main:app --host 0.0.0.0 --port 8080`
   - **HTTP Port**: 8080

### 2.3. Configurar Variables de Entorno

En **Environment Variables**, agrega:

```
DATABASE_URL=mysql+pymysql://doadmin:PASSWORD@HOST:25060/upao_timetabling?charset=utf8mb4
SECRET_KEY=tu-secret-key-aqui-cambiar
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=production
FRONTEND_URL=https://tu-app.herokuapp.com
```

### 2.4. Agregar CORS Origins

Actualiza `backend/app/main.py` para incluir tu dominio de Heroku:

```python
allow_origins=[
    "http://localhost:3000",
    "http://localhost:5173",
    "https://tu-app.herokuapp.com",  # Agregar esto
    "https://tu-backend.ondigitalocean.app"  # Agregar esto
]
```

### 2.5. Desplegar

1. Click en **Create Resources**
2. Espera 5-10 minutos
3. Tu backend estará disponible en: `https://tu-app-xxxxx.ondigitalocean.app`

### 2.6. Verificar Deployment

```bash
curl https://tu-app.ondigitalocean.app/
curl https://tu-app.ondigitalocean.app/health
```

---

## 🌐 Parte 3: Frontend en Heroku

### 3.1. Preparar Frontend

```bash
cd frontend
```

Crea `static.json`:
```json
{
  "root": "dist",
  "clean_urls": true,
  "routes": {
    "/**": "index.html"
  },
  "headers": {
    "/**": {
      "Cache-Control": "no-cache, no-store, must-revalidate"
    },
    "/assets/**": {
      "Cache-Control": "public, max-age=31536000, immutable"
    }
  }
}
```

### 3.2. Actualizar API URLs

Edita todos los archivos en `frontend/src/api/*.js`:

```javascript
// Cambiar de:
const API_BASE = 'http://localhost:8001';

// A:
const API_BASE = process.env.VITE_API_URL || 'https://tu-backend.ondigitalocean.app';
```

### 3.3. Actualizar package.json

Agrega scripts de build:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "heroku-postbuild": "npm run build"
  }
}
```

### 3.4. Crear Procfile para Frontend

`frontend/Procfile`:
```
web: npx serve dist -s -l $PORT
```

### 3.5. Agregar serve a dependencies

```bash
cd frontend
npm install serve --save
```

### 3.6. Desplegar a Heroku

```bash
# Instalar Heroku CLI si no lo tienes
# https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Crear app
heroku create upao-timetabling-frontend

# Configurar variables de entorno
heroku config:set VITE_API_URL=https://tu-backend.ondigitalocean.app -a upao-timetabling-frontend

# Configurar buildpack
heroku buildpacks:set heroku/nodejs -a upao-timetabling-frontend

# Desplegar
git subtree push --prefix frontend heroku main

# O si tienes problemas:
cd frontend
git init
git add .
git commit -m "Deploy to Heroku"
heroku git:remote -a upao-timetabling-frontend
git push heroku main
```

### 3.7. Verificar Deployment

Abre: `https://upao-timetabling-frontend.herokuapp.com`

---

## ✅ Parte 4: Verificación Final

### 4.1. Checklist

- [ ] Base de datos restaurada en Digital Ocean
- [ ] Backend desplegado y respondiendo en `/health`
- [ ] Frontend desplegado y cargando
- [ ] Login funcionando
- [ ] Generación de horarios funcionando
- [ ] Descarga de archivos Excel funcionando

### 4.2. Pruebas

1. **Test Backend**:
```bash
curl https://tu-backend.ondigitalocean.app/health
```

2. **Test Login** (desde frontend):
- Usuario: `admin`
- Password: `admin123`

3. **Test Generación**:
- Ir a "Generar Horario"
- Click en "Generar Horario Completo"
- Esperar 3-5 minutos
- Verificar que descargue el Excel

---

## 🔧 Solución de Problemas

### Backend no conecta a la BD

```bash
# Verificar conexión desde local
mysql -h your-db-host.db.ondigitalocean.com -P 25060 -u doadmin -p --ssl-mode=REQUIRED

# Ver logs en Digital Ocean
# Dashboard → Apps → tu-app → Runtime Logs
```

### Frontend no conecta al Backend

1. Verificar CORS en `backend/app/main.py`
2. Verificar `VITE_API_URL` en Heroku
3. Ver logs: `heroku logs --tail -a upao-timetabling-frontend`

### Error de CORS

Agregar en `backend/app/main.py`:
```python
allow_origins=["*"],  # Solo para testing, luego restringir
```

### Build falla en Heroku

```bash
# Limpiar cache
heroku repo:purge_cache -a upao-timetabling-frontend
git commit --allow-empty -m "Rebuild"
git push heroku main
```

---

## 📊 Monitoreo

### Digital Ocean
- **Dashboard** → Apps → tu-app → **Insights**
- Ver CPU, memoria, requests

### Heroku
```bash
heroku logs --tail -a upao-timetabling-frontend
heroku ps -a upao-timetabling-frontend
```

---

## 💰 Costos Estimados

| Servicio | Plan | Costo Mensual |
|----------|------|---------------|
| Digital Ocean DB | Basic (1GB RAM, 10GB disk) | $15 |
| Digital Ocean App | Basic (512MB RAM) | $5 |
| Heroku Dyno | Eco | $5 |
| **TOTAL** | | **$25/mes** |

---

## 🔐 Seguridad

1. **Cambiar credenciales por defecto**:
   - Usuario admin en la BD
   - SECRET_KEY en variables de entorno

2. **Habilitar SSL**:
   - Digital Ocean: Automático con App Platform
   - Heroku: Automático

3. **Restringir CORS**:
   - Solo permitir dominios específicos

4. **Configurar Firewall**:
   - Digital Ocean DB: Solo permitir conexiones desde tu App

---

## 📝 Notas Adicionales

- Los archivos generados (CSVs, Excel) se guardarán en **memoria temporal** en Digital Ocean
- Si necesitas almacenamiento persistente, considera usar **Digital Ocean Spaces** (S3-compatible)
- Los logs se mantienen por 7 días en Digital Ocean
- Considera implementar **monitoring** con Sentry o similar

---

## 🆘 Soporte

Si encuentras problemas:
1. Revisa los logs: `heroku logs --tail` o Digital Ocean Runtime Logs
2. Verifica variables de entorno
3. Prueba endpoints individualmente con `curl`
4. Revisa la conexión a la BD

