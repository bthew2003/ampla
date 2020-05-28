#!/bin/bash

sudo python3 -m compileall src/*.py

sudo cp src/__pycache__/mqttQueue.cpython-37.pyc pyc/mqttQueue.pyc
#sudo chmod +x mqttQueue.pyc

sudo cp src/__pycache__/mqttDaemon.cpython-37.pyc pyc/mqttDaemon.pyc
#sudo chmod +x mqttDaemon.pyc

sudo touch mqtt_queue.sh
sudo chmod +x mqtt_queue.sh

sudo echo -e "#!/bin/bash\n\nsudo python3 /opt/semtech/ampla/mqtt_queue/pyc/mqttDaemon.pyc --pid /var/log/mqtt_queue/mqtt_queue.pid --log /var/log/mqtt_queue/mqtt_queue.log" > mqtt_queue.sh
