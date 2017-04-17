#!/usr/bin/python
#Written by Costa Paraskevopoulos in April 2017
#Implements a client for the Instant Messaging Application
#Python 2.7 has been used (the #! line should default to version 2.7)

import sys, re, os, time, select
from socket import *
from thread import *
from termios import *
from difflib import get_close_matches

DEBUG = 1

def main():
	#creates client socket on random os-chosen port
	client_socket = socket(AF_INET, SOCK_STREAM)

	#connects to the server
	try:
		client_socket.connect((SERVER_IP, SERVER_PORT))
	except:
		print >>sys.stderr, sys.argv[0] + ': could not connect to ' + SERVER_IP + ' on port', SERVER_PORT
		client_socket.close()
		sys.exit(1)

	login(client_socket)

#user is in login state
def login(sock):
	sock.send('login\n.')
	response = sock.recv(1024)

	#username state
	if response.startswith('username'):
		username = get_input_safely('Username: ', sock)
		sock.send('username=' + username + '\n.')
		response = sock.recv(1024)
		while response.startswith('unknown user') or response.startswith('already logged in'):
			print parse_response(response)
			username = get_input_safely('Username: ', sock)
			sock.send('username=' + username + '\n.')
			response = sock.recv(1024)

	#password state
	if response.startswith('blocked'):
		print parse_response(response) #user or ip may be blocked
	elif response.startswith('password'):
		password = get_input_safely('Password: ', sock)
		sock.send('password=' + password + '\n.')
		response = sock.recv(1024)
		while response.startswith('invalid password'):
			print parse_response(response)
			password = get_input_safely('Password: ', sock)
			sock.send('password=' + password + '\n.')
			response = sock.recv(1024)
		print parse_response(response) #user ought to be blocked or logged in
	else:
		print >>sys.stderr, 'Something went wrong (error code: 111).'
		sock.close()
		sys.exit(1) #should not happen - bad server code

	#only continue with cmd prompt if logged in
	if response.startswith('logged in'):
		start_new_thread(server_transmissions, (sock,))
		wait_for_cmd(sock)
	try: #forces i/o streams to flush before program exit
		sys.stderr.close()
		sys.stdout.close()
	except IOError:
		pass
	sock.close()

#receives commands from logged-in client
def wait_for_cmd(sock):
	while 1:
		cmd = get_input_safely('> ', sock)
		cmd = cmd.rstrip().lstrip()
		backlog = ''

		#checks all possible commands
		if cmd == 'help':
			print_help()
		elif cmd == 'whoelse':
			response, backlog = contact_server(sock, 'whoelse\n.')
			print parse_response(response)
		elif re.match(r'^whoelsesince(\s.*)?$', cmd):
			m = validate(r'^whoelsesince\s+(\d+)$', cmd, NO_TIME)
			if m == None: continue
			response, backlog = contact_server(sock, 'whoelsesince=' + m.group(1) + '\n.')
			print parse_response(response)
		elif re.match(r'^broadcast(\s.*)?$', cmd):
			m = validate(r'^broadcast\s+(.+)$', cmd, EMPTY_MSG)
			if m == None: continue
			response, backlog = contact_server(sock, 'broadcast=' + m.group(1) + '\n.')
			if not response.startswith('broadcast successful'):
				print parse_response(response)
		elif re.match(r'^message(\s.*)?$', cmd):
			m = validate(r'^message\s+([^ ]+)\s+(.+)$', cmd, BAD_MSG_CMD)
			if m == None: continue
			response, backlog = contact_server(sock, 'sendto=' + m.group(1) + '\n' + m.group(2) + '\n.')
			if not response.startswith('messaging successful'):
				print parse_response(response)
		elif re.match(r'^block(\s.*)?$', cmd):
			m = validate(r'^block\s+(.+)$', cmd, BAD_BLOCK_CMD)
			if m == None: continue
			response, backlog = contact_server(sock, 'block=' + m.group(1) + '\n.')
			print parse_response(response)
		elif re.match(r'^unblock(\s.*)?$', cmd):
			m = validate(r'^unblock\s+(.+)$', cmd, BAD_UNBLOCK_CMD)
			if m == None: continue
			response, backlog = contact_server(sock, 'unblock=' + m.group(1) + '\n.')
			print parse_response(response)
		elif cmd == 'logout':
			break #socket closed in caller
		else:
			print 'Error. Invalid command.' #relieve burden on server
			suggest_closest_command(cmd)

		#prints backlog after command is over
		if backlog != '':
			print backlog

#wrapper that validates a command by checking it against a pattern
#prints error message and returns None if command does not match the pattern
#otherwise, returns the match object for further processing in caller
def validate(regex, cmd, err_msg):
	m = re.match(regex, cmd)
	if not m:
		print err_msg
		return None
	return m

#displays any server transmissions while waiting for user commands
def server_transmissions(sock):
	timed_out = 0
	global SEMAPHORE
	while 1:
		if SEMAPHORE == 1:
			continue #sleeps thread while processing client request
		SEMAPHORE = 1

		available = select.select([sock], [], [], 0)

		#waits until data is available
		if available[0]:
			response = sock.recv(1024)

			#terminates client process if server disconnects
			if response == '':
				print >>sys.stderr, 'Connection to server lost.'
				sock.close()
				os._exit(1)

			#collects server transmissions into a string
			msgs = response.split('\n.')
			server_transmissions = ''
			for msg in msgs[0:len(msgs)-1]:
				if msg.startswith('session time out'): #could occur at any time
					timed_out = 1
				server_transmissions += '\n' + parse_response(msg)
			print server_transmissions

			#quit client process if timed out
			if timed_out == 1:
				sock.close()
				os._exit(1)

			#otherwise, rewrite client prompt
			sys.stdout.write('> ')
			sys.stdout.flush()
			tcflush(sys.stdin, TCIFLUSH) #in case user enters partial cmd before server transmission

		SEMAPHORE = 0
		time.sleep(0.5) #avoid delaying main thread from acquiring lock

#filters server responses not relevant to current state
#returns response related to current state and backlog of server transmissions
#facilitates queuing of unrelated data for use after current state is ready
def handle_unrelated_data(sock):
	response = sock.recv(1024)
	backlog = ''
	msgs = response.split('\n.')

	#filters server transmissions into the backlog
	for msg in msgs[0:len(msgs)-1]:
		if msg.startswith('server transmission'):
			backlog += '\n' + parse_response(msg)
		else:
			response = msg #don't parse response in case caller needs header

	return (response, backlog)

#retrieves body of server response
#assumes first line is a header and response is terminated with '\n.'
#if there is no body, the header is returned
def parse_response(response):
	response = re.sub(r'^[^\n]+\n', '', response)
	response = re.sub(r'\n\.$', '', response)
	return response

#sends request to server and returns response and backlog
#silences the server_transmissions thread to avoid conflicts
def contact_server(sock, request):
	global SEMAPHORE
	SEMAPHORE = 1
	sock.send(request)
	response, backlog = handle_unrelated_data(sock)
	SEMAPHORE = 0
	return (response, backlog)

#prints help menu, showing all available commands and their function
def print_help():
	print '''
help ....................... show this help
whoelse .................... show list of all users currently logged in
whoelsesince <time> ........ show list of users logged in at any time within the last <time> seconds
broadcast <message> ........ send a message to all online users
message <user> <message> ... send a message to specified user
block <user> ............... block <user> from sending you messages and hide your presence from <user>
unblock <user> ............. unblock <user> if already blocked

logout ..................... logout from the Instant Messaging App
'''

#reads and returns user input from stdin using the given prompt
#closes system resources on KeyboardInterrupt
def get_input_safely(prompt, socket):
	try:
		return raw_input(prompt)
	except KeyboardInterrupt:
		socket.close()
		sys.exit(0)
	except EOFError:
		return get_input_safely('', socket) #don't reprint prompt

#uses difflib module to find the closest available command to that specified
def suggest_closest_command(cmd):
	c1 = cmd.split(' ')[0] #name of cmd
	c2 = re.sub(r'^[^ ]+', '', cmd) #args to cmd
	matches = get_close_matches(c1, ['help', 'whoelse', 'whoelsesince', 'broadcast', 'message', 'block', 'unblock', 'logout'])
	if len(matches) != 0:
		if matches[0] in ['help', 'whoelse', 'logout']:
			c2 = '' #ignore trailing chars when c1 ought to have to no args
		print 'Did you mean "' + matches[0] + c2 + '"?' #show first match only

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

	#client error message strings
	NO_TIME = 'Error. Please specify a time in seconds.'
	EMPTY_MSG = 'Error. Please enter a message body.'
	BAD_MSG_CMD = 'Error. Please specify a user and message body.'
	BAD_BLOCK_CMD = 'Error. Please specify a user to block.'
	BAD_UNBLOCK_CMD = 'Error. Please specify a user to unblock.'

	main()
