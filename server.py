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

	start_new_thread(timeout_inactive_users, (TIMEOUT,))

	#waits for client request
	while 1:
		client_socket, client_addr = server_socket.accept()
		request = client_socket.recv(1024)
		if DEBUG:
			print client_addr
		start_new_thread(client_thread, (request, client_socket, client_addr[0], client_addr[1]))

	server_socket.close()

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
			m = re.match(r'^whoelsesince=(\d+)', request) #extract time
			whoelsesince(user, request, sock, ip, port, client, int(m.group(1)))
			last_activity[sock] = (user, time.time())
		elif request.startswith('whoelse'):
			whoelse(user, request, sock, ip, port, client)
			last_activity[sock] = (user, time.time())
		elif request.startswith('broadcast='):
			m = re.match(r'^broadcast=(.*)', request) #extract msg
			broadcast(user, request, sock, ip, port, client, m.group(1))
			last_activity[sock] = (user, time.time())
		elif request.startswith('sendto='):
			m = re.match(r'sendto=(.+)\n(.+)', request) #extract user and msg
			message(user, request, sock, ip, port, client, m.group(1), m.group(2))
			last_activity[sock] = (user, time.time())
			""" ### TEMPLATE ###
		elif request.startswith(''):
			#function call
			last_activity[sock] = (user, time.time())
			"""
		else:
			if DEBUG:
				print 'Error. Client issued unknown command. Bad client code.'
			sock.send('unknown state\nUnknown command issued by client.')
		request = sock.recv(1024)

	#user has logged out
	if user in logged_in:
		logout_user(sock, user)

#logs out the user
def logout_user(client_socket, user):
	global SEMAPHORE
	while SEMAPHORE == 1:
		continue
	SEMAPHORE = 1
	del last_activity[client_socket]
	SEMAPHORE = 0
	if user in logged_in:
		del logged_in[user]
	start = session_history[user][-1][0] #append logout time to curr session
	session_history[user][-1] = (start, time.time())
	broadcast_presence(user, 'logged out')
	client_socket.close()

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
		global SEMAPHORE
		while SEMAPHORE == 1:
			continue
		SEMAPHORE = 1
		last_activity[sock] = (user, time.time())
		SEMAPHORE = 0
		sock.send('logged in\n\n!! Welcome to the Instant Messaging App !!\n')

		#send msgs received while offline
		if user in offline_msg:
			for msg in offline_msg[user]:
				sock.send('\n')
				sock.send(msg)
			del offline_msg[user] #clear offline msgs

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
		sock.send('list of users\n' + list_of_users)

#client is requesting 'whoelsesince'
def whoelsesince(current_user, request, sock, ip, port, client, t):
	list_of_users = ''
	curr_time = time.time()
	min_time = curr_time - t
	for user in session_history:
		if user == current_user:
			continue

		#need to check each session for each user
		for session in session_history[user]:
			start_of_session, end_of_session = session
			if end_of_session == '':
				end_of_session = curr_time #session not yet over

			#checks for overlapping range (condition: Ai <= Bf ^ Af >= Bi)
			if start_of_session <= curr_time and end_of_session >= min_time:
				list_of_users += user + '\n'
				break #for efficiency and to prevent duplicates

	list_of_users = list_of_users.rstrip('\n')
	if list_of_users == '':
		sock.send('No users matching that criteria found.')
	else:
		sock.send('list of users\n' + list_of_users)

#closes connection to inactive users
def timeout_inactive_users(timeout):
	global SEMAPHORE
	while 1:
		while SEMAPHORE == 1:
			continue
		SEMAPHORE = 1
		for sock in last_activity:
			user, last_use = last_activity[sock]
			curr_time = time.time()
			if curr_time - last_use > timeout:
				sock.send('session time out\nSession timed out due to inactivity.')
				SEMAPHORE = 0 #since logout_user needs to acquire the lock
				logout_user(sock, user) #changes last_activity
				break #prevents race conditions since last_activity has changed
		SEMAPHORE = 0
		time.sleep(1)

#client wants to 'broadcast' a msg
def broadcast(current_user, request, sock, ip, port, client, msg):
	global SEMAPHORE
	while SEMAPHORE == 1:
		continue
	SEMAPHORE = 1

	#since this is not a one-off lookup, use last_activity, not logged_in
	for s in last_activity:
		user = last_activity[s][0]
		if user != current_user:
			s.send('server transmission\n' + current_user + ': ' + msg)

	SEMAPHORE = 0
	sock.send('broadcast successful\nAll online users received your broadcast.')

#client wants to 'message' another user
def message(current_user, request, sock, ip, port, client, sendto, msg):
	if not sendto in passwords:
		sock.send('invalid user\nError. Invalid user.')
	elif sendto == current_user:
		sock.send('user is self\nError. Cannot send message to self.')
	elif not sendto in logged_in:
		#user is offline - store for offline delivery
		if not sendto in offline_msg:
			offline_msg[sendto] = []
		offline_msg[sendto].append(current_user + ': ' + msg)
		sock.send('messaging successful\nReceipient will see your message when they log in.')
	else:
		#user is online - send straight away
		sendto_socket = logged_in[sendto]
		sendto_socket.send('server transmission\n' + current_user + ': ' + msg)
		sock.send('messaging successful\nReceipient received your message.')

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
		sock.send('server transmission\n' + current_user + ' ' + status)

#reads and processes user information from credentials.txt
#returns a dict of (user, password) pairs
def process_credentials():
	creds = 'credentials.txt'
	if os.access(creds, os.R_OK) and os.path.isfile(creds):
		lines = open(creds, 'r').readlines()
		passwords = {}
		for line in lines:
			line = line.strip('\n')
			(user, passwd) = line.split(' ')
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
	passwords = process_credentials() #user => password
	num_user_attempts = {} #user => # wrong usernames
	num_password_attempts = {} #client => (user, # wrong passwods)
	logged_in = {} #user => socket
	blocked_for_duration = {} #ip => duration
	session_history = {} #user => (login time, logout time)
	last_activity = {} #socket => (user, time)
	offline_msg = {} #user => [msgs]

	#used to prevent race conditions for last_activity dict
	SEMAPHORE = 0

	#server messages
	TRY_AGAIN = ' Please try again later.'
	REASON = 'due to multiple unsuccessful login attempts.'
	BLOCK_USER = 'Your account has been blocked ' + REASON + TRY_AGAIN
	BLOCK_IP = 'Your IP has been blocked ' + REASON + TRY_AGAIN

	main()
