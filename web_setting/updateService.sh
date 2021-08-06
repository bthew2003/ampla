#!/bin/bash

sudo ./make_pyc.sh
echo "make pyc"

RDO_DIR="/ro"
PYC_DIR="/opt/semtech/ampla/web_setting/pyc/"
VER_DIR="/opt/semtech/ampla_Src/version"
VER2_DIR="/opt/semtech/ampla/version"
README_DIR="/opt/semtech/ampla_Src/README.md"
README2_DIR="/opt/semtech/ampla"

if [ ! -d "$RDO_DIR" ];then
  RDO_DIR=""
fi

sudo systemctl stop web_setting.service

sleep 1

sudo cp -r pyc/* ${RDO_DIR}${PYC_DIR}
echo "copy pyc "${RDO_DIR}${PYC_DIR}

sudo systemctl restart web_setting.service
echo "restart service"

sudo cp ${RDO_DIR}${VER_DIR} ${RDO_DIR}${VER2_DIR}
echo "copy Version "${RDO_DIR}${VER_DIR}   ${RDO_DIR}${VER2_DIR}

sudo cp ${RDO_DIR}${README_DIR} ${RDO_DIR}${README2_DIR}
echo "copy ReadMe "${RDO_DIR}${README_DIR}   ${RDO_DIR}${README2_DIR}

