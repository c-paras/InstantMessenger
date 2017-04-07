#!/usr/bin/python
#Written by Costa Paraskevopoulos in April 2017
#Implements a server for the Instant Messaging Application
#Python 2.7 has been used (the #! line should default to version 2.7)

import sys, re, os, time
from socket import *
from thread import *

DEBUG = 1

def main():

	#creates server socket on specified port
	server_socket = socket(AF_INET, SOCK_STREAM)
	try:
		server_socket.bind(('', SERVER_PORT))
		server_socket.listen(1)
	except:
		print >>sys.stderr, sys.argv[0] + ': port', SERVER_PORT, 'in use'
		sys.exit(1)

	#waits for client request
	while 1:
		client_socket, client_addr = server_socket.accept()
		request = client_socket.recv(1024)
		if DEBUG:
			print request
			print client_addr
		start_new_thread(client_thread, (request, client_socket, client_addr[0], client_addr[1]))

	server_socker.close()

#responds to each different client request
def client_thread(request, sock, ip, port):
	client = (ip, port)
	user = ''
	while request:
		if request == 'login':
			if ip in blocked_for_duration:
				t = int(time.time())
				print DURATION
				if t - blocked_for_duration[ip] > DURATION:
					del blocked_for_duration[ip] #unblock ip
					sock.send('username')
				else:
					sock.send('blocked ip')
			else:
				sock.send('username')
		elif request.startswith('username='):
			user = request.split('=')[1]
	
			#check if valid user
			if user in logged_in:
				sock.send('already logged in')
			elif is_valid_user(user):
				num_password_attempts[client] = (user, 1)
				if user in blocked_for_duration:
					t = int(time.time())
					if t - blocked_for_duration[user] > DURATION:
						del blocked_for_duration[user] #unblock user
						sock.send('password')
					else:
						sock.send('blocked user')
				else:
					sock.send('password')
			else:
	
				#increment # login attempts
				if client in num_user_attempts:
					num_user_attempts[client] += 1
				else:
					num_user_attempts[client] = 1
	
				#block if 3 failed attempts
				if num_user_attempts[client] == 3:
					blocked_for_duration[ip] = int(time.time())
					sock.send('blocked ip')
				else:
					sock.send('unknown user')
	
		elif request.startswith('password='):
			(user, n_attempts) = num_password_attempts[client]
			if n_attempts == 3:
				blocked_for_duration[user] = int(time.time())
				sock.send('blocked user')
			elif check_password(user, request.split('=')[1]):
				logged_in.append(user)
				sock.send('logged in')
			else:
				n_attempts += 1
				num_password_attempts[client] = (user, n_attempts)
				sock.send('invalid password')
		else:
			sock.send('Unknown command: this should not occur.')
		request = sock.recv(1024)

	#user is logged out
	if user in logged_in:
		logged_in.remove(user)
	sock.close()

#looks up user in passwords dict
def is_valid_user(user):
	if user in passwords:
		return True
	else:
		return False

#looks up password in passwords dict
def check_password(user, passwd):
	if passwords[user] == passwd:
		return True
	else:
		return False

#reads and processes user information from credentials.txt
#returns a dict of (user, password) pairs
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
		print >>sys.stderr, sys.argv[0] + ': cannot read', creds
		sys.exit(1)

if __name__ == '__main__':

	#require 3 args
	if len(sys.argv) != 4:
		args = '<server port> <block duration> <timeout>'
		print >>sys.stderr, 'Usage:', sys.argv[0], args
		sys.exit(1)

	#all args must be non-negative
	if not (sys.argv[1].isdigit() and sys.argv[2].isdigit() and sys.argv[3].isdigit()):
		print >>sys.stderr, sys.argv[0] + ': all arguments must be non-negative integers'
		sys.exit(1)

	SERVER_PORT = int(sys.argv[1])
	DURATION = int(sys.argv[2])
	TIMEOUT = int(sys.argv[3])

	passwords = process_credentials()
	num_user_attempts = {}
	num_password_attempts = {}
	logged_in = [] #will likely change to a dict for whoelsesince
	blocked_for_duration = {}

	main()
