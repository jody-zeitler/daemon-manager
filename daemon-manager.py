#!/usr/bin/env python

# An HTTP daemon manager written in Python
# Uses MongoDB for storage

import sys, os, time, shlex
from datetime import datetime
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from urllib import unquote_plus
from subprocess import Popen
from hashlib import sha1
import pymongo

mongo_tasks = None
task_list = None
task_order = None

class MyHandler(BaseHTTPRequestHandler):

	def do_GET(self):
		global task_list
		try:
			print self.path
			request = self.path
			code = 200
			response = ""
			content_type = "text/html"
			location = None

			if request == "/":
				with open("interface/index.html", "r") as f:
					response = f.read()
					response = response.replace("##TABLE##", get_tasks())
				content_type = "text/html"

			elif request == "/style.css":
				with open("interface/style.css", "r") as f:
					response = f.read()
				content_type = "text/css"

			elif request == "/script.js":
				with open("interface/script.js", "r") as f:
					response = f.read()
				content_type = "application/javascript"

			else:
				if request.startswith("/start"):
					request_split = request.split("/")
					if len(request_split) == 3:
						task_id = request_split[2]
						task_list[task_id].start()
					code = 302
					location = "/"

				if request.startswith("/stop"):
					request_split = request.split("/")
					if len(request_split) == 3:
						task_id = request_split[2]
						task_list[task_id].stop()
					code = 302
					location = "/"

				if request.startswith("/output"):
					request_split = request.split("/")
					if len(request_split) == 3:
						task_id = request_split[2]
						response = task_list[task_id].get_output()
						content_type = "text/plain"
					else:
						code = 302
						location = "/"

			self.send_response(code)
			self.send_header("Content-Type", content_type)
			if location:
				self.send_header("Location", location)
			self.end_headers()
			self.wfile.write(response)

		except IOError:
			self.send_error(404, "Not Found")

		except Exception as detail:
			print str(detail)
			self.send_error(500, "Internal Server Error")

	def do_POST(self):
		global task_list, mongo_tasks
		try:
			print self.path
			request = self.path
			response = ""

			code = 200
			content_type = "text/plain"

			if self.headers.getheader("Content-Type").startswith("application/x-www-form-urlencoded"):
				length = int(self.headers.getheader('Content-Length'))
				data = self.rfile.read(length).strip().split("&")
				fields = {}
				for field in data:
					(key, value) = field.split("=", 1)
					fields[unquote_plus(key)] = unquote_plus(value)

				if request.startswith("/save"):
					request_split = request.split("/")
					if len(request_split) == 3:
						task_id = request_split[2]

						name = fields["name"]
						cmd = fields["cmd"]
						if fields["shell"] == "true": shell = True
						else: shell = False

						if task_id == "new":
							task = Task(name, cmd, shell)
							task_id = task.id
							task_list[task.id] = task
							match = {}
						else:
							if task_id in task_list:
								(pid, returncode) = task_list[task_id].status()
								if returncode is not None:
									task_list[task_id].name = name
									task_list[task_id].cmd = cmd
									task_list[task_id].shell = shell
									match = mongo_tasks.find_one({"id": task_id})

						if match is not None:
							match["id"] = task_id
							match["name"] = name
							match["cmd"] = cmd
							match["shell"] = shell
							mongo_tasks.save(match)

			self.send_response(code)
			self.send_header("Content-Type", content_type)
			self.end_headers()
			self.wfile.write("OK")

		except IOError:
			self.send_error(404, "Not Found")

		except Exception as detail:
			print str(detail)
			self.send_error(500, "Internal Server Error")

	def log_message(self, format, *args):
		return

def get_tasks():
	global task_list, task_order
	html = "<table id='tasks'><tr><th>Name</th><th>Command</th><th>Shell</th><th></th><th>PID</th><th></th><th></th></tr>"
	for task in (task_list[task_id] for task_id in task_order):
		html += "<tr id='task_%s' class='task'><td>%s</td><td>%s</td>" % (task.id, task.name, task.cmd)

		if task.shell == True:
			html += "<td><input type='checkbox' disabled='disabled' checked/></td>"
		else:
			html += "<td><input type='checkbox' disabled='disabled'/></td>"

		(pid, returncode) = task.status()
		if returncode is not None:
			html += "<td><a class='disabledLink'>Stopped</a></td><td><a href='start/%s'>Start</a></td>" % task.id
		else:
			html += "<td><a href='stop/%s'>Stop</a></td><td><a class='disabledLink'>%s</a></td>" % (task.id, str(pid))

		if os.path.isfile("task/%s.out" % task.id):
			html += "<td><a href='output/%s' target='_blank'>Output</a></td>" % task.id
		else:
			html += "<td><a class='disabledLink'>Output</a></td>"

		if returncode is not None:
			html += "<td><a class='editTask'>Edit</a></td>"
		else:
			html += "<td><a class='disabledLink'>Edit</a></td>"

		html += "</tr>"
	html += "</table>"
	return html

class Task():
	def __init__(self, name, cmd, shell=False, id=None):
		self.name = name
		self.cmd = cmd
		self.shell = shell
		if id is None:
			m = sha1(str(time.time()) + name)
			self.id = m.hexdigest()[:16]
		else:
			self.id = id
		self.process = None
		self.outfile = None

	def start(self):
		if self.process and self.process.returncode is None:
			return None
		if self.outfile:
			self.outfile.close()

		self.outfile = open("task/"+self.id+".out", "w")
		#self.outfile.write("\n--------------------------\n")
		#self.outfile.write(str(datetime.now())+"\n")
		#self.outfile.write("--------------------------\n")
		if self.shell == False:
			cmd = shlex.split(self.cmd)
		else:
			cmd = self.cmd
		self.process = Popen(cmd, stdout=self.outfile, stderr=self.outfile, shell=self.shell)
		print "starting %s" % self.process.pid
		return self.process.pid

	def stop(self):
		if self.process:
			(pid, returncode) = self.status()
			if returncode is None:
				print "stopping %s" % pid
				self.process.terminate()
				self.process.wait()
				self.outfile.close()
				return self.process.returncode
		return None

	def kill(self):
		if self.process:
			self.process.kill()
			self.process.poll()
			self.outfile.close()
			return self.process.returncode
		else: return None

	def status(self):
		if self.process:
			self.process.poll()
			return (self.process.pid, self.process.returncode)
		else:
			return (None, 0)

	def wait(self):
		if self.process:
			self.process.wait()
			return (self.process.pid, self.process.returncode)
		else:
			return (None, 0)

	def get_output(self):
		output = "process output not found"
		with open("task/"+self.id+".out", "r") as f:
			output = f.read()
		return output

def main():
	#task = Task("ls", "ls l*", True)
	#task.start()
	#(pid, returncode) = task.status()
	#if returncode >= 0:
	#	print "%s returned %s" % (str(pid), str(returncode))
	#else:
	#	print "%s running" % str(pid)

	global mongo_tasks, task_list, task_order

	conn = pymongo.Connection()
	mongo_tasks = conn.process.tasks
	task_list = {}
	task_order = []
	for entry in mongo_tasks.find():
		task = Task(entry["name"], entry["cmd"], entry["shell"], entry["id"])
		task_list[task.id] = task
		task_order.append(task.id)

	server = HTTPServer(("", 8080), MyHandler)
	print "Started HTTPServer localhost:8080"
	try: server.serve_forever()
	except: server.socket.close()
	print "Stopped HTTPServer localhost:8080"

if __name__ == "__main__": main()