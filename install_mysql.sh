#!/bin/bash
# install_mysql.sh
# Run: bash install_mysql.sh
# Installs MySQL, starts it, sets root password to match your .env

echo ""
echo "========================================"
echo "  MySQL Auto-Installer"
echo "========================================"
echo ""

# Read password from .env
DB_PASS=$(grep "^DB_PASSWORD=" .env | cut -d'=' -f2)
echo "  Using password from .env: $DB_PASS"
echo ""

# Install
echo "[1/4] Installing MySQL..."
sudo apt-get update -qq
sudo apt-get install -y mysql-server

# Start
echo "[2/4] Starting MySQL..."
sudo service mysql start
sleep 2

# Set root password
echo "[3/4] Setting root password..."
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '$DB_PASS'; FLUSH PRIVILEGES;"

# Verify
echo "[4/4] Verifying connection..."
mysql -u root -p"$DB_PASS" -e "SELECT 'MySQL is working!' AS status;"

echo ""
echo "========================================"
echo "  Done! Now run: python main.py"
echo "========================================"
echo ""
