#!/usr/bin/env bash

sudo make clean
sudo make all
sudo systemctl stop packet-forwarder.service
sudo cp lora_pkt_fwd /opt/semtech/packet_forwarder/lora_pkt_fwd/lora_pkt_fwd
sudo systemctl start packet-forwarder.service

