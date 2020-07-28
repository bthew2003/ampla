#!/bin/bash

<<<<<<< HEAD
sudo python3 -m compileall src/*.py

sudo cp src/__pycache__/app.cpython-37.pyc pyc/app.pyc
sudo cp src/__pycache__/I2C_EEPROM_Class.cpython-37.pyc pyc/I2C_EEPROM_Class.pyc
sudo cp src/__pycache__/bTest_Class.cpython-37.pyc pyc/bTest_Class.pyc
=======
sudo python3 -m compileall src/app.py

sudo cp src/__pycache__/app.cpython-37.pyc pyc/app.pyc
#sudo chmod +x app.pyc
>>>>>>> 707f8647ebe11041216f282e384713a005d1de24

sudo touch app.sh
sudo chmod +x app.sh

sudo echo -e "#!/bin/bash\n\nsudo python3 /opt/semtech/ampla/web_setting/pyc/app.pyc" > app.sh
