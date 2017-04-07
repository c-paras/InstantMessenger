#!/usr/bin/python
#Written by Costa Paraskevopoulos in April 2017
#Implements a client for the Instant Messaging Application
#Python 2.7 has been used (the #! line should default to version 2.7)

import sys, re, os
from socket import *

DEBUG = 1

#def process_cmd_args(args):
if len(sys.argv) != 3:
	print >>sys.stderr, 'Usage:', sys.argv[0], '<server ip> <server port>'
	sys.exit(1)

if not sys.argv[2].isdigit():
	print >>sys.stderr, sys.argv[0] + ': invalid port number'
	sys.exit(1)

#connects to the server
SERVER_IP = sys.argv[1]
SERVER_PORT = int(sys.argv[2])
sock = socket(AF_INET, SOCK_STREAM) #client socket
try:
	sock.connect((SERVER_IP, SERVER_PORT))
except:
	print >>sys.stderr, sys.argv[0] + ': could not connect to ' + SERVER_IP + ' on port', SERVER_PORT
	sys.exit(1)

#log in user
sock.send('login')
response = sock.recv(1024)
if response == 'username':
	username = raw_input('Username: ')
	sock.send('username=' + username)
	response = sock.recv(1024)
	while response == 'unknown user' or response == 'already logged in':
		if response == 'unknown user':
			print 'Unknown user. Please try again.'
		else:
			print 'User is already logged in on another session.'
		username = raw_input('Username: ')
		sock.send('username=' + username)
		response = sock.recv(1024)
if response == 'blocked ip':
	print 'Your IP has been blocked due to multiple unsuccessful login attempts. Please try again later.'
elif response == 'blocked user':
	print 'Your account has been blocked due to multiple unsuccessful login attempts. Please try again later.'
elif response == 'password':
	password = raw_input('Password: ')
	sock.send('password=' + password)
	response = sock.recv(1024)
	while response == 'invalid password':
		print 'Invalid password. Please try again.'
		password = raw_input('Password: ')
		sock.send('password=' + password)
		response = sock.recv(1024)
	if response == 'blocked user':
		print 'Invalid password. Your account has been blocked. Please try again later.'
	elif response == 'logged in':
		print 'Welcome to the Instant Messaging App.'

if response != 'logged in':
	sock.close()
	sys.exit(0)

#receives commands from logged-in client 
while 1:
	cmd = raw_input('> ')
	if cmd == 'help':
		print """
help ... show this help
...
logout ... logout from the Instant Messaging App
"""
	elif cmd == 'logout':
		break
	else:
		print 'Error. Invalid command.'

sock.close()

#def main():


#if __name__ == '__main__':
#	main()
