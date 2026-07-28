# Selenium + Docker Desktop

## Requisitos

- Docker Desktop iniciado.
- Docker configurado para usar contenedores Linux.
- PowerShell abierto en esta carpeta.

## Prueba simple headless

```powershell
docker compose build
docker compose run --rm scraper
```

Los resultados aparecen en `output`.

Para cambiar la URL:

```powershell
$env:SCRAPE_URL="https://www.selenium.dev"
docker compose run --rm scraper
```

## Ejecutar directamente con Docker

```powershell
docker build -t selenium-scraper:local .

docker run --rm `
  --name selenium-scraper `
  --shm-size=2g `
  -e SCRAPE_URL="https://example.com" `
  -e HEADLESS="true" `
  -v "${PWD}/output:/app/output" `
  selenium-scraper:local
```

## Modo visible con noVNC

Iniciar Chrome y el scraper:

```powershell
docker compose -f compose.visible.yaml up --build
```

Abrir en el navegador:

```text
http://localhost:7900
```

La imagen oficial de Selenium suele usar la contraseña VNC `secret`.
Este ejemplo también configura noVNC sin contraseña mediante
`SE_VNC_NO_PASSWORD=1`.

Para detener los contenedores:

```powershell
docker compose -f compose.visible.yaml down
```

## Adaptar el script real

1. Copiar las dependencias del proyecto a `requirements.txt`.
2. Reemplazar el contenido demostrativo de `scraper.py`.
3. Conservar las opciones de Chrome para Docker.
4. Usar `/app/output` para archivos de salida.
5. Leer usuarios, contraseñas y configuración desde variables de entorno.
6. Ejecutar siempre `driver.quit()` dentro de un bloque `finally`.
7. No copiar archivos `.env`, credenciales ni cookies a la imagen.

## Comandos útiles

```powershell
docker images
docker ps -a
docker logs selenium-scraper
docker image inspect selenium-scraper:local
docker compose config
```
