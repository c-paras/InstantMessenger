#!/usr/bin/python
#Written by Costa Paraskevopoulos in April 2017
#Implements a client for the Instant Messaging Application
#Python 2.7 has been used (the #! line should default to version 2.7)

import sys, re, os, select
from socket import *
from thread import *

DEBUG = 1

def main():
	client_socket = socket(AF_INET, SOCK_STREAM) #creates client socket on random port

	#connects to the server
	try:
		client_socket.connect((SERVER_IP, SERVER_PORT))
	except:
		print >>sys.stderr, sys.argv[0] + ': could not connect to ' + SERVER_IP + ' on port', SERVER_PORT
		sys.exit(1)

	login(client_socket)

#user is in login state
def login(sock):
	sock.send('login')
	response = sock.recv(1024)

	#username state
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

	#password state
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

	#only continue with cmd prompt if logged in
	if response == 'logged in':
		start_new_thread(server_transmissions, (sock,))
		wait_for_cmd(sock)
	sock.close()

#receives commands from logged-in client
def wait_for_cmd(sock):
	while 1:
		cmd = raw_input('> ')
		cmd = cmd.rstrip()
		if cmd == 'help':
			print """
help	... show this help
whoelse	... show list of all users currently logged in
...
logout	... logout from the Instant Messaging App
"""
		elif cmd == 'whoelse':
			sock.send('whoelse')
			SEMAPHORE = 1
			response, backlog = handle_unrelated_data(sock)
			sys.stdout.write(response)
			print backlog
			SEMAPHORE = 0
			"""
		### START OF TEMPLATE ###
		elif cmd == 'placeholder':
			sock.send('placeholder=')
			SEMAPHORE = 1
			response, backlog = handle_unrelated_data(sock)
			print response
			print backlog
			SEMAPHORE = 0
		### END OF TEMPLATE ###
			"""
		elif cmd == 'logout':
			break
		else:
			print 'Error. Invalid command.'

#displays any server transmissions while waiting for user commands
def server_transmissions(sock):
	while 1:
		if SEMAPHORE == 1:
			continue #sleeps thread while processing client request

		available = select.select([sock], [], [], 1)
		if available[0]:
			response = sock.recv(1024)
			response = response.replace('server transmission\n', '')
			print response
			sys.stdout.write('> ')
			sys.stdout.flush()

#filters server responses not relevant to current state
#returns response related to current state and backlog of server transmissions
#facilitates queuing of unrelated data for use after current state is ready
def handle_unrelated_data(sock):
	response = sock.recv(1024)
	backlog = ''

	#there may be several consecutive server transmissions
	while response.startswith('server transmission'):
		response = response.replace('server transmission\n', '')
		backlog += response
		response = sock.recv(1024)

	return (response, backlog)

if __name__ == '__main__':

	#require 2 args
	if len(sys.argv) != 3:
		print >>sys.stderr, 'Usage:', sys.argv[0], '<server ip> <server port>'
		sys.exit(1)

	#port # must be non-negative
	if not sys.argv[2].isdigit():
		print >>sys.stderr, sys.argv[0] + ': invalid port number'
		sys.exit(1)

	SERVER_IP = sys.argv[1]
	SERVER_PORT = int(sys.argv[2])

	SEMAPHORE = 0 #used to sleep server_transmissions thread when handling client requests

	main()
