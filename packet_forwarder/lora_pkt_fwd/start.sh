#!/usr/bin/env bash

IOT_SK_SX1301_RESET_PIN=7

echo "Accessing concentrator reset pin through GPIO$IOT_SK_SX1301_RESET_PIN..."

WAIT_GPIO() {
	sleep 0.2
}

iot_sk_init() {
	# setup GPIO 7
	echo "$IOT_SK_SX1301_RESET_PIN" > /sys/class/gpio/export; WAIT_GPIO

	# set GPIO 7 as output
	echo "out" > /sys/class/gpio/gpio$IOT_SK_SX1301_RESET_PIN/direction; WAIT_GPIO

	# write output for SX1301 reset
	echo "1" > /sys/class/gpio/gpio$IOT_SK_SX1301_RESET_PIN/value; WAIT_GPIO
	echo "0" > /sys/class/gpio/gpio$IOT_SK_SX1301_RESET_PIN/value; WAIT_GPIO

	# set GPIO 7 as input
	echo "in" > /sys/class/gpio/gpio$IOT_SK_SX1301_RESET_PIN/direction; WAIT_GPIO
}

iot_sk_term() {
	# cleanup GPIO 7
	if [ -d /sys/class/gpio/gpio$IOT_SK_SX1301_RESET_PIN ]
	then
		echo "$IOT_SK_SX1301_RESET_PIN" > /sys/class/gpio/unexport; WAIT_GPIO
	fi
}

lsk_localServer_Check() {
	json=`cat /opt/semtech/ampla/web_setting/pyc/server`
	#echo $json

	if [[ $json == *"localhost"* ]];then
	  ./update_gwid_local.sh local_conf.json  #lsk
	  #echo "local"
	else
	  ./update_gwid.sh local_conf.json  #lsk
	  #echo "extern"
	fi
}


lsk_localServer_Check	#lsk
sleep 2

iot_sk_term
sleep 2

iot_sk_init
sleep 5

./lora_pkt_fwd


