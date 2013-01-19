An HTTP daemon manager written in Python

This is a general-purpose task manager with an HTTP interface. Obviously completely unsecure as it is, but I think it would be really handy. It saves the effort of remoting into a server to check logs and process statuses - all the information you need about a set of processes is on the page.

It uses a simple Python HTTP server as its base, and a local MongoDB database as storage for task information. Output is saved to a file, but I'm having problems with flushing subprocess buffers so it may not always be current.