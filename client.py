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

#connects to the server
server_ip = sys.argv[1]
server_port = int(sys.argv[2])
sock = socket(AF_INET, SOCK_STREAM) #client socket
sock.connect((server_ip, server_port))

sock.send('login') #user state = login

#prompt for username
response = sock.recv(1024)
if response == 'username':
	username = raw_input('Username: ')
	sock.send('username=' + username)
	while response == 'unknown user':
		print 'Unknown user. Please try again.'
		username = raw_input('Username: ')
		sock.send('username=' + username)
	if response == 'blocked':
		print "Three failed attempts.........try again alter...."

#prompt for password
response = sock.recv(1024)
if response == 'password':
	password = raw_input('Password: ')
	sock.send('password=' + password)
	response = sock.recv(1024)
	while response == 'invalid password':
		print 'Invalid password. Please try again.'
		password = raw_input('Password: ')
		sock.send('password=' + password)
		response = sock.recv(1024)
	if response == 'blocked':
		print 'Invalid password. Your account has been blocked. Please try again later.'
	elif response == 'logged in':
		print 'Welcome to the Instant Messaging App.'

#sock.close()

#def main():


#if __name__ == '__main__':
#	main()
