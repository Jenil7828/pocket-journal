RUN WITH DOCKER (Production – CMD)
1️⃣ Build image

Run from Backend\

docker build -f Dockerfile.prod -t pocket-journal:prod .

2️⃣ Run container
docker run ^
--env-file .env ^
-v "%cd%\secrets:/secrets:ro" ^
-p 8080:8080 ^
--name pocket-journal ^
pocket-journal:prod

3️⃣ Stop & remove (clean reset)
docker stop pocket-journal
docker rm pocket-journal

4️⃣ View logs
docker logs -f pocket-journal

5️⃣ Health check
curl http://127.0.0.1:8080/health

Expected:

{"status":"ok"}

docker compose -f .\docker-compose.prod.yml up -d
