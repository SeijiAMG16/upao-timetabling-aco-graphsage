# 🚀 Deployment Package - Sistema UPAO Timetabling

## ✅ Estado: Listo para Desplegar

Todo está preparado para desplegar el sistema en:
- **Backend**: Digital Ocean App Platform
- **Frontend**: Heroku
- **Base de Datos**: Digital Ocean Managed MySQL

---

## 📦 Contenido del Package

### ✅ Backend (Digital Ocean)
- `backend/Procfile` - Configuración de ejecución
- `backend/runtime.txt` - Python 3.11
- `backend/.env.example` - Template de variables de entorno
- `backend/backup_upao_timetabling_20251201_185228.sql` - **Backup completo de BD (0.45 MB)**
- `backend/requirements.txt` - Dependencias
- `backend/app/main.py` - CORS configurado para deployment

### ✅ Frontend (Heroku)
- `frontend/Procfile` - Configuración de ejecución con serve
- `frontend/static.json` - Configuración de serving estático
- `frontend/.env.example` - Template de variables de entorno
- `frontend/package.json` - Actualizado con serve y heroku-postbuild
- Todas las APIs actualizadas para usar `import.meta.env.VITE_API_URL`

### ✅ Documentación
- **`DEPLOYMENT_GUIDE.md`** - Guía completa con instrucciones paso a paso
- **`DEPLOYMENT_COMMANDS.md`** - Comandos copiar-pegar para deployment rápido
- **`DEPLOYMENT_SUMMARY.md`** - Resumen ejecutivo
- Este archivo (`DEPLOYMENT_README.md`)

---

## 🎯 Quick Start

### Opción 1: Seguir la guía completa
```bash
# Abrir la guía paso a paso
start DEPLOYMENT_GUIDE.md
```

### Opción 2: Comandos rápidos
```bash
# Abrir comandos copiar-pegar
start DEPLOYMENT_COMMANDS.md
```

---

## 📋 Orden de Deployment Recomendado

### 1️⃣ Base de Datos (15-20 min)
- Crear Managed Database MySQL en Digital Ocean
- Descargar CA Certificate
- Restaurar backup: `backend\backup_upao_timetabling_20251201_185228.sql`
- Verificar tablas y datos

**Costo**: $15/mes (Basic plan)

### 2️⃣ Backend (10-15 min)
- Crear App en Digital Ocean App Platform
- Conectar repositorio GitHub
- Configurar variables de entorno
- Esperar deployment automático
- Probar endpoints `/` y `/health`

**Costo**: $5/mes (Basic XXS)

### 3️⃣ Frontend (10-15 min)
- Instalar Heroku CLI
- Crear app en Heroku
- Configurar `VITE_API_URL` con URL del backend
- Deploy con git
- Probar acceso y login

**Costo**: $5/mes (Eco dyno)

### 4️⃣ Configuración Final (5 min)
- Actualizar CORS en backend con URL de frontend
- Probar flujo completo: Login → Generar Horario → Descargar Excel
- Configurar dominios custom (opcional)

**Costo Total**: ~$25/mes

---

## 🔑 Variables de Entorno Necesarias

### Backend (Digital Ocean)
```bash
DATABASE_URL=mysql+pymysql://doadmin:PASSWORD@HOST:25060/upao_timetabling?charset=utf8mb4
SECRET_KEY=tu-secret-key-seguro-cambiar-esto
ENVIRONMENT=production
CORS_ORIGINS=https://tu-frontend.herokuapp.com,https://tu-backend.ondigitalocean.app
FRONTEND_URL=https://tu-frontend.herokuapp.com
```

### Frontend (Heroku)
```bash
VITE_API_URL=https://tu-backend.ondigitalocean.app
```

---

## ✨ Características del Sistema Desplegado

- ✅ **Generación automática de horarios** con ACO optimizado
- ✅ **299/311 secciones asignadas** (96.1% de cobertura)
- ✅ **46 profesores** con horarios individuales
- ✅ **Descarga automática** de Excel formato profesores
- ✅ **Validación de restricciones** hard y soft
- ✅ **Interface web** responsive con Material-UI
- ✅ **API REST** documentada con FastAPI/Swagger
- ✅ **Base de datos** con backup completo restaurable

---

## 🔧 Verificación Post-Deployment

### Backend
```bash
# Health check
curl https://tu-backend.ondigitalocean.app/health

# API Docs
https://tu-backend.ondigitalocean.app/docs
```

### Frontend
1. Abrir: https://tu-frontend.herokuapp.com
2. Login con: `admin` / `admin123`
3. Navegar a "Generar Horario"
4. Click "Generar Horario Completo"
5. Esperar 3-5 minutos (10 hormigas, 20 iteraciones)
6. Verificar descarga automática del Excel

### Base de Datos
```bash
mysql -h your-host.db.ondigitalocean.com -P 25060 -u doadmin -p
USE upao_timetabling;
SELECT COUNT(*) FROM course_sections;  # Debe mostrar 311
SELECT COUNT(*) FROM professors;        # Debe mostrar 57
SELECT COUNT(*) FROM classrooms;        # Debe mostrar 39
```

---

## 📊 Datos Incluidos en el Backup

- ✅ **311 secciones** de cursos (297 base + 14 subgrupos)
- ✅ **57 profesores** con restricciones horarias
- ✅ **39 aulas** (teoría, práctica, laboratorio)
- ✅ **96 franjas horarias** (Lunes-Sábado, 7:00-22:00)
- ✅ **Restricciones de profesores** configuradas
- ✅ **Asignaciones previas** si existen
- ✅ **Currículos y liguas** para validación

---

## 🆘 Solución de Problemas

### Error: "Cannot connect to database"
```bash
# Verificar URL de conexión
echo $DATABASE_URL

# Probar conexión directa
mysql -h HOST -P 25060 -u doadmin -p --ssl-mode=REQUIRED
```

### Error: "CORS policy blocked"
```bash
# Verificar variable CORS_ORIGINS incluye ambas URLs
heroku config -a tu-frontend
# Debe incluir: https://tu-frontend.herokuapp.com
```

### Frontend no carga
```bash
# Ver logs
heroku logs --tail -a tu-frontend

# Rebuild si es necesario
heroku repo:purge_cache -a tu-frontend
git commit --allow-empty -m "Rebuild"
git push heroku main
```

### Backend lento
```bash
# Verificar recursos en Digital Ocean
# Dashboard → Apps → tu-app → Insights
# Si CPU > 80%, considerar upgrade a plan superior
```

---

## 📈 Próximos Pasos (Opcional)

1. **Dominios Custom**
   - Frontend: Configurar en Heroku
   - Backend: Configurar en Digital Ocean
   - Actualizar CORS_ORIGINS

2. **SSL Certificates**
   - Automático en ambos servicios
   - Verificar con: https://www.ssllabs.com/ssltest/

3. **Monitoring**
   - Heroku: New Relic o Papertrail
   - Digital Ocean: Built-in Insights
   - Sentry para error tracking

4. **Backups Automáticos**
   - Digital Ocean: Configurar daily backups
   - Retention: 7 días incluido

5. **CI/CD**
   - GitHub Actions para tests automáticos
   - Auto-deploy desde main branch

---

## 📞 Soporte

- **Guía Completa**: `DEPLOYMENT_GUIDE.md`
- **Comandos Rápidos**: `DEPLOYMENT_COMMANDS.md`
- **Resumen Ejecutivo**: `DEPLOYMENT_SUMMARY.md`

---

## 💡 Notas Importantes

1. **El backup es MySQL**, no PostgreSQL
2. **Archivos generados (CSV/Excel)** son temporales en Digital Ocean
3. **Para almacenamiento persistente**, usar Digital Ocean Spaces
4. **Los logs** se mantienen 7 días en Digital Ocean, 168 hrs en Heroku
5. **Cambiar credenciales por defecto** después del primer deploy
6. **SECRET_KEY** debe ser diferente en producción

---

## ✅ Checklist Final

- [ ] Backup de BD restaurado en Digital Ocean
- [ ] Backend desplegado y respondiendo en `/health`
- [ ] Frontend desplegado y cargando
- [ ] Variables de entorno configuradas
- [ ] CORS configurado correctamente
- [ ] Login funcionando (admin/admin123)
- [ ] Generación de horarios funcionando
- [ ] Descarga de Excel funcionando
- [ ] Dominios custom configurados (opcional)
- [ ] Monitoring configurado (opcional)

---

## 🎉 ¡Listo para Producción!

El sistema está completamente preparado para despliegue. Sigue las instrucciones en **DEPLOYMENT_COMMANDS.md** para comandos exactos o **DEPLOYMENT_GUIDE.md** para instrucciones detalladas.

**Tiempo estimado total de deployment**: 45-60 minutos
**Costo mensual**: ~$25 USD
