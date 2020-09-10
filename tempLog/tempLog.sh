#!/bin/bash

# Selective Variable

LOGDIR='/var/log' # 로그 디렉토리
LOG='tempLog' # 로그 파일명
ERRLOGDIR='/var/log' # 에러로그 디렉토리
ERRLOG='tempError' # 에러로그 파일명
TEMPDIR=/sys/class/thermal/thermal_zone0/temp # cpu온도 디렉토리

# Variable
NOW=$(date +"%T")
LOGNAME=$(date +"%y_%m_%d"_$LOG)
NOWERROR=$(date +"%y/%m/%d_%T")
NATURALTEMP=$(cat $TEMPDIR)
div=1000
TEMP=$(echo $NATURALTEMP $div | awk '{printf"%.1f",$1/$2}')

GPUTEMP=$(sudo /opt/vc/bin/vcgencmd measure_temp)
GPUTEMP=${GPUTEMP}
GPUTEMP=${GPUTEMP//temp=/}

for ((;;))
do
	NOW=$(date +"%T")
	LOGNAME=$(date +"%y_%m_%d"_$LOG)
	NOWERROR=$(date +"%y/%m/%d_%T")
	NATURALTEMP=$(cat $TEMPDIR)
	div=1000
	TEMP=$(echo $NATURALTEMP $div | awk '{printf"%.1f",$1/$2}')

	# Command
	if [ -f $TEMPDIR ];then
  	echo [ $NOW ] "cpu:"$TEMP"'C", "gpu:"$GPUTEMP  >> $LOGDIR/$LOG/$LOGNAME.log
	  if ! [ $? = 0 ];then
	    echo [ $NOWERROR ":" FAILED to write $LOG log ] >> $ERRLOGDIR/$ERRLOG.log
	  fi
	else
	  echo [ $NOWERROR ":" FAILED to get temparature in $LOG log ] >> $ERRLOGDIR/$ERRLOG.log
	fi

	sleep 60
done
