#!/bin/bash

sudo python3 -m compileall src/app.py

sudo cp src/__pycache__/app.cpython-37.pyc pyc/app.pyc
#sudo chmod +x app.pyc

sudo touch app.sh
sudo chmod +x app.sh

<<<<<<< HEAD
sudo echo -e "#!/bin/bash\n\nsudo python3 /opt/semtech/ampla/web_setting/pyc/app.pyc" > app.sh
=======
sudo echo -e "#!/bin/bash\n\nsudo python3 /opt/semtech/ampla/web_setting/pyc/app.pyc &" > app.sh
>>>>>>> 56c5bd7a32ba86a49fccdae0bc842e5477264c92
