#!/bin/bash

sudo python3 -m compileall src/*.py

sudo cp src/__pycache__/I2C_LCD_Class.cpython-37.pyc pyc/I2C_LCD_Class.pyc

sudo cp src/__pycache__/I2C_EEPROM_Class.cpython-37.pyc pyc/I2C_EEPROM_Class.pyc

sudo cp src/__pycache__/bTest_Class.cpython-37.pyc pyc/bTest_Class.pyc

sudo cp src/__pycache__/pCheck.cpython-37.pyc pyc/pCheck.pyc
#sudo chmod +x pCheck.pyc

sudo cp src/__pycache__/pCheckDm.cpython-37.pyc pyc/pCheckDm.pyc
#sudo chmod +x pCheckDm.pyc

sudo touch pCheckDm.sh
sudo chmod +x pCheckDm.sh

sudo echo -e "#!/bin/bash\n\nsudo python3 /opt/semtech/ampla/process_check/pyc/pCheckDm.pyc --pid /var/log/process_check/process_check.pid --log /var/log/process_check/process_check.log" > pCheckDm.sh





