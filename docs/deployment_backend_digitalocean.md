# Manual de despliegue Backend en DigitalOcean (Droplet)


Este manual documenta el despliegue del backend FastAPI en un droplet de DigitalOcean usando Docker, con soporte completo para ACO y GraphSAGE (PyTorch y torch-geometric incluidos, igual que en local).

## 1) Requisitos

- Droplet Ubuntu 22.04/24.04 con acceso SSH.
- DNS opcional (si se usará dominio).
- Base de datos MySQL 8.0 (DigitalOcean Managed MySQL o propia).
- Archivo de entrada `inputs/Libro1.xlsx` cargado en el servidor (si se usará carga local).

## 2) Preparación del servidor

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release; echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

## 3) Clonar repositorio en el droplet

```bash
git clone <URL_DEL_REPO>
cd upao-timetabling-aco-graphsage
```

## 4) Variables de entorno del backend

Crear `backend/.env` en el servidor (a partir de `backend/.env.example`):

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Ejemplo recomendado:

```env
DATABASE_URL=mysql+pymysql://USUARIO:PASSWORD@HOST:3306/upao_timetabling?charset=utf8mb4&ssl-mode=REQUIRED
SECRET_KEY=CAMBIA_ESTO_POR_UN_SECRETO_LARGO
ENVIRONMENT=production
CORS_ORIGINS=https://tu-frontend.herokuapp.com
FRONTEND_URL=https://tu-frontend.herokuapp.com
```

Notas:
- Si usas DigitalOcean Managed MySQL, la opción `ssl-mode=REQUIRED` es correcta. El backend limpia ese parámetro automáticamente.
- El endpoint `/api/algorithm/execute` requiere PyTorch. Si no instalas PyTorch, ese endpoint retornará 503 (es esperado).


## 5) Construir y levantar el backend (con PyTorch y GraphSAGE)

El Dockerfile ya instala PyTorch y torch-geometric (CPU) y usa `requirements.txt` completo, igual que tu entorno local.

```bash
docker compose -f docker-compose.backend.yml up -d --build
```

Verificar estado:

```bash
docker compose -f docker-compose.backend.yml ps
```

Ver logs:

```bash
docker compose -f docker-compose.backend.yml logs -f backend
```

## 6) Firewall

Si expones directamente el puerto 8000:

```bash
sudo ufw allow 8000/tcp
sudo ufw enable
```

## 7) (Opcional) Nginx + HTTPS

Si quieres HTTPS en el droplet, añade un reverse proxy (Nginx) y usa Certbot. No está incluido en este manual para mantenerlo simple.

## 8) Actualizaciones

```bash
git pull
docker compose -f docker-compose.backend.yml up -d --build
```

## 9) Problemas comunes

- **Falla al instalar PyTorch/torch-geometric**: el Dockerfile ya instala PyTorch y torch-geometric (CPU) y usa `requirements.txt`. Si tienes problemas, revisa la RAM del droplet (mínimo 2GB recomendado) y la conectividad a los repositorios de PyTorch y PyG.
- **Base de datos no conecta**: valida `DATABASE_URL` y que el droplet tenga salida a la red.
- **CORS**: revisa `CORS_ORIGINS` y que el frontend use HTTPS.
