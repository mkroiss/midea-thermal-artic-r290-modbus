#!/bin/bash
# Upload configuration to Home Assistant - restart required
PI="makro@192.168.178.107"
scp configuration.yaml $PI:/tmp/
ssh $PI "sudo cp /tmp/configuration.yaml /root/homeassistant/config/configuration.yaml"
echo "Done! Restart HA: ssh $PI \"sudo docker restart home-assistant\""
