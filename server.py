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
		server_socket.listen(10)
	except:
		print >>sys.stderr, sys.argv[0] + ': port', SERVER_PORT, 'in use'
		sys.exit(1)

	#waits for client request
	while 1:
		client_socket, client_addr = server_socket.accept()
		request = client_socket.recv(1024)
		if DEBUG:
			print client_addr
		start_new_thread(client_thread, (request, client_socket, client_addr[0], client_addr[1]))

	server_socker.close()

#responds to each different client request
def client_thread(request, sock, ip, port):
	client = (ip, port)
	user = ''
	while request:
		if request == 'login':
			login_state(request, sock, ip, port, client)
		elif request.startswith('username='):
			user = username_state(request, sock, ip, port, client)
		elif request.startswith('password='):
			password_state(request, sock, ip, port, client)
		elif request.startswith('whoelsesince='):
			m = re.match('whoelsesince=(\d+)', request) #extract time
			whoelsesince(user, request, sock, ip, port, client, int(m.group(1)))
		elif request.startswith('whoelse'):
			whoelse(user, request, sock, ip, port, client)
		else:
			if DEBUG:
				print 'unknown state\nThis should not occur. Bad client code.'
			sock.send('unknown state\nThis should not occur. Bad client code.')
		request = sock.recv(1024)

	#user has logged out
	if user in logged_in:
		del logged_in[user]
		start = session_history[user][-1][0] #append logout time to curr session
		session_history[user][-1] = (start, time.time())
		broadcast_presence(user, 'logged out')
	sock.close()

#client is in login state
def login_state(request, sock, ip, port, client):
	if ip in blocked_for_duration:
		t = int(time.time())
		if t - blocked_for_duration[ip] > DURATION:
			del blocked_for_duration[ip] #unblock ip
			sock.send('username')
		else:
			sock.send('blocked ip\n' + BLOCK_IP)
	else:
		sock.send('username')

#client is in username state
def username_state(request, sock, ip, port, client):
	user = request.split('=')[1]

	#check if valid user
	if user in logged_in:
		sock.send('already logged in\nUser is already logged in on another session.')
	elif is_valid_user(user):
		num_password_attempts[client] = (user, 1)

		#handle blocked user
		if user in blocked_for_duration:
			t = int(time.time())
			if t - blocked_for_duration[user] > DURATION:
				del blocked_for_duration[user] #unblock user
				sock.send('password')
			else:
				sock.send('blocked user\n' + BLOCK_USER)
		else:
			sock.send('password')

	else:

		#increment # login attempts
		if client in num_user_attempts:
			num_user_attempts[client] += 1
		else:
			num_user_attempts[client] = 1

		#block ip after 3 failed attempts
		if num_user_attempts[client] == 3:
			blocked_for_duration[ip] = int(time.time())
			sock.send('blocked ip\n' + BLOCK_IP)
		else:
			sock.send('unknown user\nUnknown user. Please try again.')

	return user

#client is in password state
def password_state(request, sock, ip, port, client):
	(user, n_attempts) = num_password_attempts[client]

	if n_attempts == 3:
		#block user after 3 failed attempts
		blocked_for_duration[user] = int(time.time())
		sock.send('blocked user\n' + BLOCK_USER)
	elif check_password(user, request.split('=')[1]):
		#password correct - log in the user
		logged_in[user] = sock
		if not user in session_history:
			session_history[user] = [] #create a list for this user's login history
		session_history[user].append((time.time(), ''))
		sock.send('logged in\nWelcome to the Instant Messaging App.')
		broadcast_presence(user, 'logged in')
	else:
		#password wrong - another failed attempt
		n_attempts += 1
		num_password_attempts[client] = (user, n_attempts)
		sock.send('invalid password\nInvalid password. Please try again.')

#client is requesting 'whoelse'
def whoelse(current_user, request, sock, ip, port, client):
	list_of_users = ''
	for user in logged_in:
		if user != current_user:
			list_of_users += user + '\n'
	list_of_users = list_of_users.rstrip('\n')
	if list_of_users == '':
		sock.send('No other users are currently logged in.')
	else:
		sock.send('List of Users\n' + list_of_users)

#client is requesting 'whoelsesince'
def whoelsesince(current_user, request, sock, ip, port, client, t):
	list_of_users = ''
	curr_time = time.time()
	min_time = curr_time - t
	print '\n'
	for user in session_history:
		print user
		if user == current_user:
			continue

		#need to check each session for each user
		for session in session_history[user]:
			print session
			start_of_session = session[0]
			end_of_session = session[1]
			if end_of_session == '':
				end_of_session = curr_time #session not yet over

			#checks for overlapping range (condition: Ai <= Bf ^ Af >= Bi)
			if start_of_session <= curr_time and end_of_session >= min_time:
				print 'another user: ' + user
				list_of_users += user + '\n'
				break #for efficiency and to prevent duplicates

	list_of_users = list_of_users.rstrip('\n')
	if list_of_users == '':
		sock.send('No users matching that criteria found.')
	else:
		sock.send('List of Users:\n' + list_of_users)

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

#sends presence notification to all logged-in users
def broadcast_presence(current_user, status):
	for user in logged_in:
		if user == current_user:
			continue
		sock = logged_in[user]
		sock.send('server transmission\n' + current_user + " " + status)

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

	#globals
	passwords = process_credentials()
	num_user_attempts = {}
	num_password_attempts = {}
	logged_in = {}
	blocked_for_duration = {}
	session_history = {}

	#server messages
	TRY_AGAIN = ' Please try again later.'
	REASON = 'due to multiple unsuccessful login attempts.'
	BLOCK_USER = 'Your account has been blocked ' + REASON + TRY_AGAIN
	BLOCK_IP = 'Your IP has been blocked ' + REASON + TRY_AGAIN

	main()
