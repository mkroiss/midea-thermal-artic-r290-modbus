#!/bin/bash
# Upload dashboard to Home Assistant - no restart needed, just refresh browser
PI="makro@192.168.178.107"
scp heat_pump_dashboard.yaml $PI:/tmp/
ssh $PI "sudo cp /tmp/heat_pump_dashboard.yaml /root/homeassistant/config/heat_pump_dashboard.yaml"
echo "Done! Refresh your browser to see changes."
