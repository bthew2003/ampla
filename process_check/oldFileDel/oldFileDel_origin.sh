#!/bin/sh

backupCNT=100
DIR="/opt/semtech/bMsg"

ls $DIR -l | grep .msg | wc -l > A.txt
A=$(cat A.txt)
echo $A

if [ $A -lt $backupCNT ]; then
	echo "Count is low (" $A ")"
else
	echo "Count is High (" $A ")"
	ls $DIR -lt | grep .msg > imsy.txt
	sed '1,'"$backupCNT"'d' imsy.txt | awk '{print $9}' > imsy2.txt
	#cat imsy2.txt
		for fileName in $(cat imsy2.txt)
		do
		echo "Delete " $fileName
		rm -rf $DIR/$fileName
		done
fi

rm -rf imsy.txt
rm -rf imsy2.txt
rm -rf A.txt
