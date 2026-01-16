#!/bin/bash
# Qmanga Auto-Install Script for Ubuntu/Oracle Cloud
# Run: curl -sSL <url> | bash

echo "🚀 Bắt đầu cài đặt Qmanga..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3 python3-pip python3-venv git

# Clone or create app directory
sudo mkdir -p /opt/qmanga
sudo chown $USER:$USER /opt/qmanga

# If you have git repo, uncomment:
# git clone https://github.com/YOUR_USERNAME/qmanga.git /opt/qmanga

echo "📦 Cài đặt Python dependencies..."
cd /opt/qmanga
python3 -m venv venv
source venv/bin/activate
pip install httpx beautifulsoup4 fastapi uvicorn[standard] pydantic

# Create systemd service
echo "⚙️ Tạo service..."
sudo tee /etc/systemd/system/qmanga.service > /dev/null <<EOF
[Unit]
Description=Qmanga Server
After=network.target

[Service]
User=$USER
WorkingDirectory=/opt/qmanga/backend
ExecStart=/opt/qmanga/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable qmanga
sudo systemctl start qmanga

# Open firewall
sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT

echo ""
echo "✅ Cài đặt hoàn tất!"
echo "🌐 Truy cập: http://YOUR_SERVER_IP:8000"
echo ""
echo "📝 Các lệnh hữu ích:"
echo "   sudo systemctl status qmanga  - Xem trạng thái"
echo "   sudo systemctl restart qmanga - Khởi động lại"
echo "   sudo journalctl -u qmanga -f  - Xem logs"
