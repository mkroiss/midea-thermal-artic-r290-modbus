#!/bin/bash
# Upload heat pump package to Home Assistant - restart required
PI="makro@192.168.178.107"
scp heat_pump_package_target_control.yaml $PI:/tmp/
ssh $PI "sudo cp /tmp/heat_pump_package_target_control.yaml /root/homeassistant/config/heat_pump_package_target_control.yaml"
echo "Done! Restart HA: ssh $PI \"sudo docker restart home-assistant\""
