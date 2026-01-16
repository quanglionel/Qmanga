# Qmanga - Personal Manga Reader

A personal manga reading application inspired by Tachiyomi, built with FastAPI backend and vanilla HTML/CSS/JS frontend.

## Features

- 📚 **Multi-source Support**: Aggregates manga from 7+ Vietnamese and English sources
- 🔔 **Notifications**: Get notified when followed manga has new chapters
- 📥 **Auto-download**: Automatically preloads new chapters for offline reading
- 📖 **Library Management**: Track your reading progress
- 🎨 **Premium UI**: Dark mode, customizable accent colors

## Quick Start (Local Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
cd backend
python main.py

# Open browser at http://localhost:8000
```

## Deploy with Docker

```bash
# Build image
docker build -t qmanga .

# Run container
docker run -d -p 8000:8000 -v qmanga_data:/app/data --name qmanga qmanga
```

## Deploy to VPS (Ubuntu/Debian)

1. **SSH to your server**
```bash
ssh user@your-server-ip
```

2. **Install dependencies**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv nginx certbot python3-certbot-nginx
```

3. **Clone and setup**
```bash
git clone <your-repo-url> /opt/qmanga
cd /opt/qmanga
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. **Create systemd service**
```bash
sudo nano /etc/systemd/system/qmanga.service
```

Add:
```ini
[Unit]
Description=Qmanga Server
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/qmanga/backend
ExecStart=/opt/qmanga/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

5. **Start service**
```bash
sudo systemctl enable qmanga
sudo systemctl start qmanga
```

6. **Configure Nginx**
```bash
sudo nano /etc/nginx/sites-available/qmanga
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

7. **Enable site and get SSL**
```bash
sudo ln -s /etc/nginx/sites-available/qmanga /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d your-domain.com
```

## Deploy to Railway (Free)

1. Connect your GitHub repo to Railway
2. Add environment variable: `PORT=8000`
3. Deploy automatically

## Data Persistence

The following files store user data:
- `user_library.json` - Followed manga
- `reading_history.json` - Reading history
- `notifications.json` - Notifications
- `chapter_cache.json` - Cached chapters

For production, consider mounting a volume or using a database.

## Sources

| Source | Language | Status |
|--------|----------|--------|
| Otruyen | VI | ✅ |
| NetTruyen | VI | ✅ |
| TruyenQQ | VI | ✅ |
| BlogTruyen | VI | ⚠️ |
| MangaDex | EN | ✅ |
| Comick | EN | ✅ |
| CManga | VI | ✅ |

## ⚠️ Disclaimer

This application is for personal use only. Do not deploy publicly as it may violate copyright laws. The developer is not responsible for any misuse.
