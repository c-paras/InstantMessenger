#!/usr/bin/python
#Written by Costa Paraskevopoulos in April 2017
#Implements a server for the Instant Messaging Application
#Python 2.7 has been used (the #! line should default to version 2.7)

import sys, re, os
from socket import *

DEBUG = 1

def main():
	if len(sys.argv) != 4:
		args = '<server port> <block duration> <timeout>'
		print >>sys.stderr, 'Usage:', sys.argv[0], args
		sys.exit(1)

	#creates server socket on specified port
	server_port = int(sys.argv[1])
	server_socket = socket(AF_INET, SOCK_STREAM)
	try:
		server_socket.bind(('', server_port))
		server_socket.listen(1)
	except:
		print >>sys.stderr, sys.argv[0] + ': port', sys.argv[1], 'in use'
		sys.exit(1)

	#waits for client request
	while 1:
		client_socket, client_addr = server_socket.accept()
		request = client_socket.recv(1024)
		if DEBUG:
			print request
			print client_socket
			print client_addr
		while 1:
			handle_request(request, client_socket, client_addr[0], client_addr[1])
			request = client_socket.recv(1024)

#sock.close()

#responds to each different client request
def handle_request(request, sock, ip, port):
	client = (ip, port)
	if request == 'login':
		sock.send('username')
	elif request.startswith('username='):
		user = request.split('=')[1]
		if is_valid_user(user):
			num_password_attempts[client] = (user, 1)
			sock.send('password')
		else:
			if client in num_username_attempts and num_username_attempts[client] == 3:
				sock.send('blocked')
			else:
				sock.send('unknown user')
			if client in num_username_attempts:
				num_username_attempts[client] += 1
			else:
				num_username_attempts[(ip, port)] = 1
	elif request.startswith('password='):
		(user, n_attempts) = num_attempts[client]
		if n_attempts == 3:
			#TODO: implement blocking here......
			sock.send('blocked')
		if check_password(user, request.split('=')[1]):
			logged_in.append(user)
			sock.send('logged in')
		else:
			n_attempts += 1
			num_password_attempts[client] = (user, n_attempts)
			sock.send('invalid password')
	else:
		sock.send('Unknown command: this should not occur.')

def is_valid_user(user):
	if user in passwords:
		return True
	else:
		return False

def check_password(user, passwd):
	if passwords[user] == passwd:
		return True
	else:
		return False

#reads and stores user information from credentials.txt in a dict
def process_credentials():
	creds = 'credentials.txt'
	if os.access(creds, os.R_OK) and os.path.isfile(creds):
		lines = open(creds, 'r').readlines()
		passwords = {}
		for line in lines:
			line = line.strip('\n')
			(user, passwd) = line.split(" ")
			passwords[user] = passwd
		return passwords
	else:
		print >>sys.stderr, sys.argv[0], ': cannot read', creds
		sys.exit(1)

if __name__ == '__main__':
	passwords = process_credentials()
	num_username_attempts = {}
	num_password_attempts = {}
	logged_in = []
	main()
