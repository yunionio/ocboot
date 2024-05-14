sudo systemctl disable --now k3s
sudo /usr/local/bin/k3s-uninstall.sh
sudo rm -rf /etc/rancher/k3s
sudo rm -rf /var/lib/rancher/k3s
sudo rm -f /usr/local/bin/k3s
sudo rm -f /etc/systemd/system/k3s.service
sudo rm -f /etc/systemd/system/k3s-agent.service
sudo systemctl daemon-reload
sudo pkill -f k3s
