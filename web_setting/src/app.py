#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os, sys
import string
import socket, fcntl, struct
import subprocess
import re, uuid
import time
import threading

from flask import Flask, url_for, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta
from werkzeug.utils import secure_filename
from snCheck import SNCHECK

#from flask_login import LoginManager, login_require, login_user, logout_user

#Flask Initialize
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///webUser.db'
app.config['CA_UPLOAD_FOLDER'] = '/opt/semtech/ampla/tls/uploadFile/ca'
app.config['CRT_UPLOAD_FOLDER'] = '/opt/semtech/ampla/tls/uploadFile/crt'
app.config['KEY_UPLOAD_FOLDER'] = '/opt/semtech/ampla/tls/uploadFile/key'

app.config['CA_REAL_FOLDER'] = '/opt/semtech/ampla/tls/ca'
app.config['CRT_REAL_FOLDER'] = '/opt/semtech/ampla/tls/crt'
app.config['KEY_REAL_FOLDER'] = '/opt/semtech/ampla/tls/key'
db = SQLAlchemy(app)

#Absolute Path
roFlag = 0
jsonPath = '/opt/semtech/packet_forwarder/lora_pkt_fwd'
dhcpFile = '/etc/dhcpcd.conf'
wpaFile = '/etc/wpa_supplicant/wpa_supplicant.conf'
nsFile = '/etc/chirpstack-gateway-bridge/chirpstack-gateway-bridge.toml'	#Chirpstack-gateway-bridge

geuidTag = "gateway_ID"
ethStatTag = "# Example static IP configuration:"
nsTag = "servers="


#Previous Value
g_wlanList = [["",""], ["", ""]]
g_Serial = ""
g_Version = ""
g_sAdd = list(range(3))
g_ipList = list(range(3))
g_StaticList = list(range(2))

g_applyFlag = 0

#[reset, upload, setEth,
exeFlag = [0,0,0,0,0,0,0]		#실행 할 동작 예약


#####################################################################################
# Class
#####################################################################################
class User(db.Model):
	""" Create user table"""
	id = db.Column(db.Integer, primary_key=True)
	useridx = db.Column(db.String(80), unique=True)
	username = db.Column(db.String(80))
	password = db.Column(db.String(80))
	print ("id : " + username + " / pw : " + password)

	def __init__(self, useridx, username, password):
		self.useridx = useridx
		self.username = username
		self.password = password

#####################################################################################
# Session Timeout Function
#####################################################################################
@app.before_request
def make_session_permanent():
	SESSION_TIMEOUT = 30
	session.permanent = True
	app.permanent_session_lifetime = timedelta(minutes=SESSION_TIMEOUT)

#####################################################################################
# Route Function
#####################################################################################
@app.route('/', methods=['GET', 'POST'])
def home():
	""" Session control"""
	global exeFlag
	print ("Home")

	try:
		if session['logged_in'] == False:
			return render_template('login.html')

		#Page render 하고 나서 2초 후 실행
		sum = 0
		for e in exeFlag:
			sum += e

		if sum != 0:
			threading.Timer(2, execThread).start()

		return render_template('index.html', val=getData())

	except:
		return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
	"""Login Form"""
	print ("Login")

	try:
		if request.method == 'GET':
			return render_template('login.html')

		else:
			name = request.form['username']
			passw = request.form['password']

			data = User.query.filter_by(username=name, password=passw).first()
			if data is not None:
				session['logged_in'] = True

			else:
				flash("Log-in Fail")
				return redirect(url_for('login'))

	except:
		print ("Error_login")

	return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
	"""Register Form"""
	print ("Regiter")

	try:
		if request.method == 'POST':
			#new_user = User(username=request.form['username'], password=request.form['password'])
			#new_user = User(username='hsrnd', password='hsrnd000')	#Test
			data = User.query.filter_by(username=request.form['username']).first()

			if data == None:
				new_user = User(username=request.form['username'], password=request.form['password'])
				db.session.add(new_user)
				db.session.commit()

			return redirect(url_for('home'))

	except:
		print ("Error_register")

	return render_template('register.html')

@app.route('/modify', methods=['GET', 'POST'])
def modify():
	"""Modify Form"""
	print ("Modify")

	try:
		if request.method == 'POST':
			print ("Modify Post")

			name = request.form['username']
			passw = request.form['password']
			print (name + " / " + passw)

			data = User.query.filter_by(username=name, password=passw).first()
			if data is not None:
				data.username = request.form['newusername']
				data.password = request.form['newpassword']
				db.session.commit()
				flash('Modify Success')
				return redirect(url_for('home'))

			else:
				flash('Modify Fail')
				return redirect(url_for('home'))
		return render_template('modify.html')

	except:
		flash('Modify Error')
		return render_template('modify.html')

@app.route('/logout')
def logout():
	"""Logout Form"""
	flash("Log-out")
	session['logged_in'] = False
	return redirect(url_for('home'))

###############################################################################################################

#write\apply Func
@app.route('/writeapply/<str>', methods=['POST'])
def writeapply(str):
	global g_wlanList, exeFlag, g_sAdd, g_applyFlag

	if g_applyFlag == 1:	return 0

	if request.method == 'POST':
		if str == 'apply':
			print ("=================== apply ====================")

			g_applyFlag = 1
			uploadChk = True

			try:
				sAdd = list(range(3))
				sAdd[0] = request.form['sAdd']				#Server Address
				sAdd[1] = request.form['sPort']				#Server Port
				sAdd[2] = request.form.get('tlsChk')	#tls Use Check
				eth0Chk = request.form.get('eSChk')		#Eth0 Static Check
				eth0Add = request.form['eStatic']			#Eth0 Static Address
				wfList = [ [request.form['wfID'], request.form['wfPW'] ], [ request.form['wfID2'], request.form['wfPW2'] ] ]

				#TLS Check
				if sAdd[2] == None:
					sAdd[2] = "0"
				else:
					sAdd[2] = "1"
					uploadChk = tlsFileUpload()

				print ("================>Step_1")

				#uploadChk = True

				#Server Address 또는 Port 또는  Tls 가 기존과 다를 때
				if g_sAdd != sAdd or uploadChk:
					g_sAdd = sAdd

					#file Write
					writeServerAddr(nsFile, g_sAdd)

				else:
					print ("Same Address")

				print ("================>Step_2")

				#Static Ethernet Setting 예외처리 필요 (FileWrite)
				setEthernet(eth0Chk, eth0Add)

				print ("================>Step_3")

				#Wi-fi 이전 값과 다를때 (FileWrite)
				setWlan(wfList)

				print ("================>Step_4")

				if uploadChk == False:	flash("Apply Complete (TLS File Upload Fail)")
				else:	flash("Apply Complete")

			except:
				flash("Apply Fail")

			finally:
				g_applyFlag = 0
				exeFlag[0] = 1

		elif str == 'reset':
			exeFlag[0] = 1

		elif str == 'upload':
			try:
				clonePath = "/opt/semtech/gitclone"
				localPath = "/opt/semtech"

				if True == os.path.isdir(clonePath):
					subprocess.check_output(['sudo', 'rm', '-r', clonePath])

				subprocess.check_output(['sudo', 'mkdir', '-p', clonePath + '/ampla'])
				subprocess.check_output(['sudo', 'git', 'config', '--global', 'http.sslVerify', 'false'])
				subprocess.check_output(['sudo', 'git', 'clone', 'https://github.com/bthew2003/ampla.git', clonePath + '/ampla'])

				verList = ["", ""]
				if True == os.path.isfile(clonePath + "/ampla/version"):	verList[0] = readFileList(clonePath + "/ampla/version")
				if True == os.path.isfile(localPath + "/ampla/version"):	verList[1] = readFileList(localPath + "/ampla/version")

				if verList[0] != verList[1]:
					subprocess.check_output('sudo rm ' + clonePath + '/ampla/web_setting/pyc/server', shell=True)
					subprocess.check_output('sudo rm ' + clonePath + '/ampla/web_setting/pyc/*.db', shell=True)
					subprocess.check_output('sudo cp -r ' + clonePath + '/ampla/. ' + localPath + '/ampla', shell=True)
					exeFlag[1] = 1

					if True == os.path.isdir('/ro'):
						os.system("sudo mount -o remount,rw /ro")
						subprocess.check_output('sudo cp -r ' + localPath + '/ampla/. /ro' + localPath + '/ampla', shell=True)

					print ("Copy Complete")

				else:
					print ("Same Version")

				subprocess.check_output(['sudo', 'rm', '-r', clonePath])
				#print ("Delete Clone Folder")

				flash("Upload Complete")
				exeFlag[0] = 1

			except:
				#print ("Error_upload")
				flash("Upload Fail")

	return redirect(url_for('home'))


#########################################################################
# Local Function
#########################################################################
def initProcess():
	try:
		print ("initProcess")
		getData()
		setData()

	except:
		print ("Except initProcess")

def initDefUser():
	try:
		#data = User.query.filter_by(username='ampla').first()
		data = User.query.filter_by(useridx='admin').first()
		if data == None:
			new_user = User(useridx='admin', username='ampla', password='ampla000') #Test
			db.session.add(new_user)
			db.session.commit()
			#print ("make Default User")

#		initProcess()
	except:
		print ("Except_initDefUser")

#File 안에서 String 찾기(Find Name, Find Item)
def findStrInFile(fName, fItem):
	try:
		fp = open(fName, mode='r')
		lines = fp.readlines()
		fp.close()

		result = ""
		for idx, val in enumerate(lines):
			if val.find(fItem) != -1:
				result = val

		return result
	except:
		print ("Except_findStrInFile")

#File 을 개행 문자 별로 List에 담기(Find Name, Find String)
def readFileList(fName):
	L = []
	try:
		fp = open(fName, mode='r')
		while(1):
			line=fp.readline()
			try:escape=line.index('\n')
			except:escape=len(line)

			if line:	L.append(line[0:escape])
			else:	break;
		fp.close()
	except:
		print ("Except_readFileList")

	return L

#List에서 특정 문자열이 있는 index 찾기
def findStrList(listName, fStr):
	try:
		idx = 0
		for i in listName:
			str = i.strip()
			tIdx = str.find(fStr)
			if tIdx == 0:
				#print ("find : " + str(idx))
				break;
			else:
				idx += 1
				pass

		if len(listName) == idx:	return -1
		else:	return idx

	except:
		print ("Error_findStrList")

def getWlan():
	try:
		s = SNCHECK()
		wList = [[s.getSSID1(), s.getPASSWD1()], [s.getSSID2(), s.getPASSWD2()]]
		return wList

	except:
		print ("Error_getWlan")
		return None


def getServerAddr():
	try:
		s = SNCHECK()
		return [s.getServ(), s.getPort(), s.getTLS()]

	except:
		print ("Except Server Address Read Fail")

		return None

def getTLS():
	try:
		tList = list(range(3))

		tList[0] = os.listdir(app.config['CA_UPLOAD_FOLDER'])[0]
		tList[1] = os.listdir(app.config['CRT_UPLOAD_FOLDER'])[0]
		tList[2] = os.listdir(app.config['KEY_UPLOAD_FOLDER'])[0]

		return tList

	except:
		print ("Except TLS File Name Get Fail")

		return None


def getIpAddr(network):
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		#ipaddr = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', network[:15]))[20:24])  #python2
		ipaddr = socket.inet_ntoa(fcntl.ioctl(s.fileno(), \
																					0x8917, \
																					struct.pack('256s', bytes(network[:15], 'utf-8')))[20:24])	#python3
	except IOError:
		ipaddr = "127.0.0.1"

	s.close()
	return ipaddr

def getSerial():
	try:
		s = SNCHECK()
		return  s.getSerialNum()

	except:
		print ("Error_getSerial")
		return None

def getNicIp():
	try:
		ipList = list(range(3))

		#eth0 Address Read
		ipList[0] = "{0:>14}".format(getIpAddr('eth0')).replace(" ", "")

		#wlan0 Address Read
		ipList[1] = "{0:>14}".format(getIpAddr('wlan0')).replace(" ", "")

		#wwan0 Address Read
		ipList[2] = "{0:>14}".format(getIpAddr('wwan0')).replace(" ", "")

		return ipList

	except:
		print ("Except_getNicIp")
		return None

def getVersion():
	try:
		readStr = os.popen('cat /opt/semtech/ampla/version').read()
		version = readStr[0:readStr.find("\n")].rstrip()
		return version[version.find(':')+1:len(version)].strip()

	except:
		print ("Except Version Read")
		return None

def getStaticCheck():
		try:
			sList = list(range(2))
			s = SNCHECK()
			sList[0] = s.getDHCP()
			sList[1] = s.getStaticIp()
			if ipCheck(sList[1]) == False:	sList[1] = "127.0.0.1"
			return sList
		except:
			print ("Except getStaticCheck")
			return None

def setData():
	global g_wlanList, g_ipList, g_Serial, g_sAdd, g_StaticList

	try:
		print ("\n\n---- SetData --------------------------------------------")
		print ("nsFile : " + nsFile)
		print ("g_sAdd : " + str(g_sAdd))

		writeServerAddr(nsFile, g_sAdd)
		os.system("sudo systemctl restart chirpstack-gateway-bridge.service")

	except:
		print ("Except setData")


def getData():
	global g_wlanList, g_ipList, g_Serial, g_sAdd, g_StaticList

	try:
		#NIC Address Read
		g_ipList = getNicIp()

		#Serial Read
		g_Serial = getSerial()

		#Ethernet Static Read
		g_StaticList = getStaticCheck()

		#Wifi ssid, pw
		g_wlanList = getWlan()

		#Server Address Read
		g_sAdd = getServerAddr()

		#TLS Certificate
		g_tlsList = getTLS()

		#Version
		g_Version = getVersion()

		print ("	---- GetData ----------------------------------------------------------")

		try:
			print ("	IP ADDRESS	: " + str(g_ipList))
			print ("	SERIAL NUM	: " + g_Serial)
			print ("	STAIC CHECK	: " + str(g_StaticList))
			print ("	WIFI ID/PW	: " + str(g_wlanList))
			print ("	SERVER ADDR	: " + str(g_sAdd))
			print ("	TLS FILE  	: " + str(g_tlsList))
			print ("	VERSION    	: " + g_Version)
		except:
			print ("Except_print_Value")

		#List에 데이터 담기
		lData = [g_ipList[0], g_ipList[1], g_ipList[2], g_Serial, g_StaticList[0], g_StaticList[1], \
						 g_wlanList[0][0], g_wlanList[0][1], g_wlanList[1][0], g_wlanList[1][1], \
						 "0", g_sAdd[0], g_sAdd[1], g_sAdd[2], g_tlsList[0], g_tlsList[1], g_tlsList[2], "false", g_Version]

		print ("\n---- GetData (send) ---------------------------------------------------")
		print (str(lData))

		return lData

	except:
		print ("Except GetData")

def ipCheck(str):
	try:
		if re.match('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', str) != None:	return True
		else:	return False
	except:
		print ("Except_ipCheck")
		return False

def setEthernet(chk, eth0add):
	global g_StaticList

	try:
		if chk == None: chk = "0"
		else:						chk = "1"

		print ("!!!! " + eth0add)
		print ("!!!! " + g_StaticList[1])

		print (g_StaticList[0])
		print (chk)

		if g_StaticList[0] != chk or g_ipList[0] != eth0add:
			print ("ethernet Change ")

			fp = open(dhcpFile, mode='r')
			readList = readFileList(dhcpFile)
			fp.close()

			dotIdx = eth0add.rfind('.')
			routers = str(eth0add[0:dotIdx + 1]) + "1"

			fSIdx = findStrList(readList, ethStatTag)
			if fSIdx > 0:		fCIdx = fSIdx
			else:						fCIdx = 0

			#ethernet Setting
			cmmt = ""
			if "0" == chk:	cmmt = "#"

			readList[fCIdx] = ethStatTag

			if fCIdx == 0:	#static / dhcp 둘다 없음
				print ("not Find Setting")
				readList.append(readList[fCIdx])
				readList.append(cmmt + "interface eth0")
				readList.append(cmmt + "static ip_address=" + eth0add + "/24")
				readList.append(cmmt + "static routers=" + routers)
				readList.append(cmmt + "static domain_name_servers=8.8.8.8 1.1.1.1 1.0.0.1")
			else:
				readList[fCIdx+1] = cmmt + "interface eth0"
				readList[fCIdx+2] = cmmt + "static ip_address=" + eth0add + "/24"
				readList[fCIdx+3] = cmmt + "static routers=" + routers
				readList[fCIdx+4] = cmmt + "static domain_name_servers=8.8.8.8 1.1.1.1 1.0.0.1"

			try:
				fp = open(dhcpFile, mode='w')
				fp.write('\n'.join(readList))
				fp.close()
				exeFlag[2] = 1

				g_StaticList[0] = chk
				g_StaticList[1] = eth0add

				s = SNCHECK()
				s.setDHCP(g_StaticList[0])
				s.setStaticIp(g_StaticList[1])
				print ("Ethernet Set")

			except:
				print ("Except setEthernet File Wirte")

	except:
		print ("Ethernet Set Except!!")

	return 0;

def setWlan(wfList):
	global g_wlanList

	try:
		print ("wlan_Debug")

		if g_wlanList != wfList:
			print ("wlan_Set")

			scan="	scan_ssid=0"
			psk="	psk=\"" + wfList[0][1] + "\""
			key_mgmt="	key_mgmt=WPA-PSK"
			if wfList[0][1] == '':  key_mgmt = "  key_mgmt=NONE"

			psk2="	psk=\"" + wfList[1][1] + "\""
			key_mgmt2="	key_mgmt=WPA-PSK"
			if wfList[1][1] == '':  key_mgmt2 = "	key_mgmt=NONE"

			cmmt = ""
			lineStr = ["ctrl_interface=DIR=/var/run/wpa_supplicant", "update_config=1","country=US", ""]

			if len(wfList[0][0].split()) == 0:  cmmt = "#"
			lineStr.extend([cmmt + "network={", cmmt + "	ssid=\"" + wfList[0][0]  + "\"", cmmt + scan, cmmt + psk, cmmt + key_mgmt, cmmt + "	priority=100", cmmt + "}", ""])

			if len(wfList[1][0].split()) == 0:  cmmt = "#"
			lineStr.extend([cmmt + "network={", cmmt + "	ssid=\"" + wfList[1][0]  + "\"", cmmt + scan, cmmt + psk2, cmmt + key_mgmt2, cmmt + "	priority=90", cmmt + "}"])

			try:
				#Read-Write Change
				#if True == os.path.isdir('/ro'):	os.system("sudo mount -o remount,rw /ro")
				fp = open(wpaFile, mode='w+')
				fp.write('\n'.join(lineStr))
				fp.close()
				exeFlag[3] = 1

				#Write EEPROM Wifi SSID/PASSWD
				s = SNCHECK()
				s.setSSID1(wfList[0][0])
				s.setPASSWD1(wfList[0][1])
				s.setSSID2(wfList[1][0])
				s.setPASSWD2(wfList[1][1])

			except:
				print ("Error_forceMakefile")

			g_wlanList = wfList

	except:
		print ("wlan Except")

def writeServerAddr(fName, addr):
	try:
		if os.path.isfile(fName):
			fp = open(fName, mode='r')
			lines = fp.readlines()
			fp.close()

			print ("w0")

			#list의전체 갯수
			#print ('전체 Line수= %d'%len(lines))
			fLine = -1

			#TLS 주석 처리...
			cmmnt = ""
			if "0" == addr[2]:	cmmnt = "#"
			print ("==============>TLS : " + cmmnt)

			caTag = "on the server (e.g. when self generated)"
			for idx, val in enumerate(lines):
				if val.find(caTag) != -1:
					lines[idx + 1] = cmmnt + lines[idx + 1].replace("#", "")
					print (lines[idx + 1])

			certTag = "mqtt TLS certificate file (optional)"
			for idx, val in enumerate(lines):
				if val.find(certTag) != -1:
					lines[idx + 1] = cmmnt + lines[idx + 1].replace("#", "")
					print (lines[idx + 1])

			keyTag = "mqtt TLS key file (optional)"
			for idx, val in enumerate(lines):
				if val.find(keyTag) != -1:
					lines[idx + 1] = cmmnt + lines[idx + 1].replace("#", "")
					print (lines[idx + 1])

			#전체 Line 중 'servers='가  포함 된Line 찾기
			for idx, val in enumerate(lines):
				if val.find("servers=") != -1:
					fLine = idx
			#print ('Find Line(%d)'%fLine)

			#입력 받은 값이 없거나 찾는 문자열이 없으면..건너 뜀
			if fLine >= 0:
				if "1" == addr[2] : servers = "		servers=[\"ssl://" + addr[0] + ":" + addr[1] + "\"]\n"
				else :              servers = "		servers=[\"tcp://" + addr[0] + ":" + addr[1] + "\"]\n"

				del lines[fLine]  #기존 Index 삭제
				lines.insert(fLine, servers)

				fp = open(fName, mode='w+t')
				fp.writelines(lines)
				fp.close()

				#Server Address EEPROM Write
				s = SNCHECK()
				s.setServ(addr[0])
				s.setPort(addr[1])
				s.setTLS(addr[2])

				subprocess.run(['sudo', 'systemctl', 'restart', 'packet-forwarder.service'])
				subprocess.run(['sudo', 'systemctl', 'restart', 'chirpstack-gateway-bridge.service'])
				print ("chirpstack_Reset")

	except:
		print ("Error_filewrite")

	finally:
		return redirect(url_for('home'))

def tlsFileCopyRestore():
	try:
		if False == os.path.isdir('/home/restore'):	os.system("sudo mkdir /home/restore")

		os.system("sudo mount /dev/mmcblk0p2 /home/restore")
		os.system("sudo cp -r /opt/semtech/ampla/tls /home/restore")
		os.system("sudo umount /home/restore")
		os.system("sudo rm -r /home/restore")
		print ("tlsFileCopyRestore_Complete")

	except:
		print ("Except_tlsFileCopyRestore")


def tlsFileUpload():
	result = True
	tlsList = [['cafile', app.config['CA_UPLOAD_FOLDER'], app.config['CA_REAL_FOLDER'], 'ca.crt'],
						 ['crtfile', app.config['CRT_UPLOAD_FOLDER'], app.config['CRT_REAL_FOLDER'], 'client.crt'],
						 ['keyfile', app.config['KEY_UPLOAD_FOLDER'], app.config['KEY_REAL_FOLDER'], 'client.key']]

	try:
		for i in range(3):
			file = request.files[tlsList[i][0]]
			if file:
				if allowed_file(file.filename, tlsList[i][0]):
					filename = secure_filename(file.filename)
					os.system("sudo rm " + tlsList[i][1] + "/*" )  #기존파일 삭제
					file.save(os.path.join(tlsList[i][1], filename))
					cmd = "sudo cp -r " + tlsList[i][1] + "/" + filename + " " + tlsList[i][2] + "/" + tlsList[i][3]
					print ("=============>cmd:" + cmd)
					os.system("sudo mkdir -p " + tlsList[i][2])
					os.system("sudo cp -r " + tlsList[i][1] + "/" + filename + " " + tlsList[i][2] + "/" + tlsList[i][3])  #기존파일 삭제
					print (tlsList[i][0] + " File Remove and Upload Complete")

				else:
					result = False
					print (tlsList[i][0] + " File Allowed Fail")
			else:	print (tlsList[i][0] + " File None")

	except:
		result = False
		print ("Except tlsFileUpload")

	if True == result:
		#TLS File Upload => Restore Partition
		tlsFileCopyRestore()

	return result

def execThread():
	global exeFlag
	print ("eThread!!!!!!!!!!!")

	try:
		if exeFlag[3] == 1:
			print ("exeFlag_3 : wlan0 Restart")
			exeFlag[3] = 0
			#os.system("sudo ifconfig wlan0 down")
			os.system("sudo ifconfig wlan0 down")
			time.sleep(3)
			os.system("sudo ifconfig wlan0 up")
			time.sleep(3)

		if exeFlag[2] == 1:
			print ("exeFlag_2 : eth0 Restart")
			exeFlag[2] = 0
			os.system("sudo ifconfig eth0 down")
			time.sleep(2)
			os.system("sudo ifconfig eth0 up&")
			time.sleep(2)

		if exeFlag[1] == 1:
			print ("exeFlag_1 : Service Restart")
			exeFlag[1] = 0
			subprocess.check_output('sudo systemctl restart process_check.service', shell=True)
			subprocess.check_output('sudo systemctl restart web_setting.service', shell=True)

		if exeFlag[0] == 1:
			print ("exeFlag_0")
			exeFlag[0] = 0
			subprocess.check_output(['sudo', 'systemctl', 'stop', 'process_check.service'])
			time.sleep(1)
			subprocess.check_output(['sudo', 'systemctl', 'reboot'])
			os.system('sudo systemctl reboot')
			sys.exit(1)

	except:
		print ("Except_execThread")

EXTENSIONS_CA = set(['crt', 'cer', 'csr', 'pem', 'der'])
EXTENSIONS_CRT = set(['crt', 'cer', 'csr', 'pem', 'der'])
EXTENSIONS_KEY = set(['key', 'pem','der'])
def allowed_file(filename, extension):
	try:
		#return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
		if extension == 'cafile':  result = '.' in filename and filename.rsplit('.', 1)[1] in EXTENSIONS_CA
		elif extension == 'crtfile':	result = '.' in filename and filename.rsplit('.', 1)[1] in EXTENSIONS_CRT
		elif extension == 'keyfile':  result = '.' in filename and filename.rsplit('.', 1)[1] in EXTENSIONS_KEY
		print ("=======>allowed_file")
		print (result)

		return result
	except:
		print ("Except allowed_file")
		return False

if __name__ == '__main__':
	app.debug = False
	db.create_all()
	app.secret_key = "5731"
	initDefUser()
	app.run(host='0.0.0.0', port=5050, debug=False)

	print ("exit2")
	sys.exit()
