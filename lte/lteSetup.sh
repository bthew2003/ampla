#!/bin/bash

#Lte_Module_Reset
reset_Lte(){
	gpio -g mode 36 out

	gpio -g write 36 1
	sleep 6
	gpio -g write 36 0
}

#qmi_network Setup
set_qmi_network(){
  qmi-network /dev/cdc-wdm0 stop
  sleep 2

  service ModemManager stop
  sleep 1

  ip link set dev wwan0 down

  echo Y | sudo tee -a /sys/class/net/wwan0/qmi/raw_ip
  sleep 1

  qmi-network /dev/cdc-wdm0 start
  sleep 2

  ip link set dev wwan0 up
	sleep 4

	returnStr=$(sudo qmicli -d /dev/cdc-wdm0 --wds-get-current-settings)
	#echo "============>" ${returnStr}

	ip4Add="${returnStr#*IPv4 address: }"
	ip4Add="${ip4Add%%IPv4 subnet mask:*}"
	#echo ${ip4Add}

	ip4Mask="${returnStr#*IPv4 subnet mask: }"
	ip4Mask="${ip4Mask%%IPv4 gateway address:*}"
	#echo ${ip4Mask}

	ip4Gateway="${returnStr#*IPv4 gateway address: }"
	ip4Gateway="${ip4Gateway%%IPv4 primary DNS:*}"
	#echo ${ip4Gateway}

	sudo ifconfig wwan0 ${ip4Add} netmask ${ip4Mask}
	#echo "ip Config"

	#sudo route add default gw ${ip4Gateway} netmask 255.255.255.0 dev wwan0
	sudo route add default gw ${ip4Gateway} netmask 0.0.0.0 dev wwan0
	#sudo route add default wwan0
	#sudo route add default eth0
	#echo "gw Route Config"

	sudo ifmetric wwan0 606
	#echo "wwan ifmetric down"
}

#Network metric Priority Setup
set_network_metric(){
	#returnStr=$(cat /etc/dhcpcd.conf)
	returnStr=$(</etc/dhcpcd.conf)
	#echo $returnStr

	getStr="${returnStr#*network_Priority }"
	#echo ${getStr}

	metric=("303" "303" "303")
	metric[$getStr]="101"
	#echo ${metric[getStr]}

	sudo ifmetric eth0 ${metric[0]}
	sudo ifmetric wlan0 ${metric[1]}
	sudo ifmetric wwan0 ${metric[2]}
}

###################################################################################### 
#telit usb Check
	lsList=$(lsusb)
	#echo $lsList

	if [[ $lsList =~ "Telit" ]]; then
		echo "Telit Module mounted"
	else
		echo "Telit Module not mounted"
		reset_Lte
	fi

#cdc-wdm0 Check
  devList=$(ls /dev)
  #echo $devList

  if [[ $devList =~ "cdc-wdm0" ]]; then
		echo "cdc-wdm0 is mounted!!"
    set_qmi_network
  else
    echo "cdc-wdm0 is not mounted!!"
  fi

#	set_network_metric
