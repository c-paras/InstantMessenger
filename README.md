# InstantMessenger
Implements an instant messaging application, featuring online and offline messaging, presence notifications, blacklisting and secure user authentication

This application was built and tested on Ubuntu 64-bit 16.04 LTS using Python version 2.7.12.

* The server application can be launched by running
```
./server.py <server port> <block duration> <timeout>
```
where the `server port` is greater than 1023 and the `block duration` and `timeout` are non-negative.

* The client application can be launched by running
```
./client.py <server ip> <server port>
```
where the `server ip` can be found by running `hostname -I` on the device running the server and using the same `server port` chosen when the server was launched.

Copyright (C) 2017 Costa Paraskevopoulos

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
