#!/usr/bin/python
#Written by Costa Paraskevopoulos in April 2017
#Implements a client for the Instant Messaging Application
#Python 2.7 has been used (the #! line should default to version 2.7)

import sys, re, os, select
from socket import *
from thread import *
from termios import *

DEBUG = 1

def main():
	#creates client socket on random os-chosen port
	client_socket = socket(AF_INET, SOCK_STREAM)

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
	if response.startswith('username'):
		username = raw_input('Username: ')
		sock.send('username=' + username)
		response = sock.recv(1024)
		while response.startswith('unknown user') or response.startswith('already logged in'):
			print parse_response(response)
			username = raw_input('Username: ')
			sock.send('username=' + username)
			response = sock.recv(1024)
	else:
		print >>sys.stderr, 'Something went wrong (error code: 111).'
		sys.exit(1)

	#password state
	if response.startswith('blocked'):
		print parse_response(response) #user or ip may be blocked
	elif response.startswith('password'):
		password = raw_input('Password: ')
		sock.send('password=' + password)
		response = sock.recv(1024)
		while response.startswith('invalid password'):
			print parse_response(response)
			password = raw_input('Password: ')
			sock.send('password=' + password)
			response = sock.recv(1024)
		print parse_response(response) #user ought to be blocked or logged in
	else:
		print >>sys.stderr, 'Something went wrong (error code: 222).'
		sys.exit(1)

	#only continue with cmd prompt if logged in
	if response.startswith('logged in'):
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
help .................. show this help
whoelse ............... show list of all users currently logged in
whoelsesince <time> ... show list of users logged in at any time within the last <time> seconds
......
logout ................ logout from the Instant Messaging App
"""
		elif cmd == 'whoelse':
			contact_server(sock, 'whoelse')
		elif cmd.startswith('whoelsesince'):
			m = re.match(r'^whoelsesince (\d+)$', cmd)
			if not m:
				print 'Error. Please specify a time in seconds.'
				continue
			contact_server(sock, 'whoelsesince=' + m.group(1))
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

		#waits until data is available
		if available[0]:
			response = sock.recv(1024)

			#terminates client process if server disconnects
			if response == '':
				print >>sys.stderr, 'Connection to server lost.'
				os._exit(1)

			response = parse_response(response)
			print response
			sys.stdout.write('> ')
			sys.stdout.flush()
			tcflush(sys.stdin, TCIFLUSH) #in case user enters partial cmd before server transmission

#filters server responses not relevant to current state
#returns response related to current state and backlog of server transmissions
#facilitates queuing of unrelated data for use after current state is ready
def handle_unrelated_data(sock):
	response = sock.recv(1024)
	backlog = ''

	#there may be several consecutive server transmissions
	while response.startswith('server transmission'):
		response = parse_response(response)
		backlog += response
		response = sock.recv(1024)

	return (response, backlog)

#retrieves body of server response
#assumes first line is a header
#if there is no body, the header is returned
def parse_response(response):
	response = re.sub(r'^[^\n]+\n', '', response)
	return response

#sends request to server and prints response and backlog
#silences the server_transmissions thread to avoid conflicts
def contact_server(sock, request):
	sock.send(request)
	SEMAPHORE = 1
	response, backlog = handle_unrelated_data(sock)
	sys.stdout.write(parse_response(response))
	print backlog
	SEMAPHORE = 0

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

	#used to sleep server_transmissions thread when handling client requests
	SEMAPHORE = 0

	main()
