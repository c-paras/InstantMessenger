#!/bin/sh
#Written by Costa Paraskevopoulos in April 2017
#Tries to break the Instant Messaging Application

cmds='whoelse whoelsesince message broadcast block unblock'

main() {
	if test $# -ne 1
	then
		echo "Usage: $0 <server port>" >&2
		exit 1
	fi

	rm -f cmds_*

	echo Generating client commands...
	while read user pass
	do
		gen_rand_cmds $user $pass
	done < credentials.txt
	sleep 1

	echo Initiating clients...
	while read user pass
	do
		run_client $user $1 > out_$user &
	done < credentials.txt

	rm -f /tmp/user_$$
}

#selects random user from available users
get_rand_user() {
	j=1
	r=`cat credentials.txt | wc -l`
	r=`shuf -n1 -i1-$r`
	while read user pass
	do
		if test $j -eq $r
		then
			echo $user
			break
		fi
		j=$(($j + 1))
	done < credentials.txt
}

#creates cmds$user file for $user
gen_rand_cmds() {

	echo $1 > cmds_$1 #user
	echo $2 >> cmds_$1 #pass

	#appends between 5 and 20 random cmds
	for i in $(seq $(shuf -n1 -i5-20))
	do
		rnd=`shuf -n1 -e $cmds`
		if test $rnd = 'whoelse'
		then
			: #nothing to add to 'whoelse'
		elif test $rnd = 'whoelsesince'
		then
			r=`shuf -n1 -i0-100` #append time in secs
			rnd="$rnd $r"
		elif test $rnd = 'message'
		then
			get_rand_user > /tmp/user_$$
			r=`cat /tmp/user_$$`
			rnd="$rnd $r `uuidgen`" #append rnd msg
		elif test $rnd = 'broadcast'
		then
			rnd="$rnd `uuidgen`" #append rnd msg
		elif test $rnd = 'block' -o $rnd = 'unblock'
		then
			get_rand_user > /tmp/user_$$
			r=`cat /tmp/user_$$`
			rnd="$rnd $r"
		fi
		echo $rnd >> cmds_$1
	done

	#always logout
	echo logout >> cmds_$1
}

#launch client process for $user
run_client() {
	cat cmds_$1 | ./client.py localhost $2
}

main "$@"
