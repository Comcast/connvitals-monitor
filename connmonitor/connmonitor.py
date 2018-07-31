# Copyright 2018 Comcast Cable Communications Management, LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
A monitor for connection vitals, based on the connvitals program.
"""
import sys
import signal
import time
import multiprocessing
from connvitals import utils, collector, ports, traceroute

def optionalFlagParse(raw:str) -> bool:
	"""
	Parses the allowed values for the optional JSON and TIMESTAMP
	configuration flags, and returns their value as a boolean.
	"""
	try:
		return bool(int(raw))
	except ValueError:
		try:
			return {"FALSE": False, "TRUE": True}[raw]
		except KeyError:
			raise ValueError("Invalid value: %s" % raw)

# This maps parsing tokens to actions to take on their values
config = {"PING": float,
          "TRACE": float,
          "SCAN": float,
          "NUMPINGS": int,
          "PAYLOAD": int,
          "HOPS": int,
          "JSON": optionalFlagParse,
          "TIMESTAMP": optionalFlagParse}

class Config():
	"""
	This extends the configuration options provided by connvitals to include
	sleep durations for each type of statistic.
	"""
	HOPS = 30
	JSON = False
	NUMPINGS = 10
	PAYLOAD = b'The very model of a modern Major General.'
	PING = 500.0
	SCAN = 0.0
	TIMESTAMP = True
	TRACE = 0.0

	def __init__(self,**kwargs):
		"""
		An extremely simple initializer that sets the objects attributes
		based on the passed dictionary of arguments.
		"""
		self.__dict__.update(kwargs)

	def __repr__(self) -> str:
		"""
		Prints out all options of a configuration
		"""
		return "Config(%s)" % ", ".join("%s=%r" % (k, v) for k,v in self.__dict__.items() )

class Collector(collector.Collector):
	"""
	The connvitals-monitor collector, that overrides parts of the
	connvitals collector.
	"""

	def run(self):
		"""
		Called when the thread is run
		"""

		# Determine output headers now to save time later
		self.plaintextHdr = self.hostname
		if self.host[0] != self.hostname:
			self.plaintextHdr += " " + self.host[0]

		if self.conf.TIMESTAMP:
			self.jsonHdr = '{"addr":"%s","name":"%s","timestamp":%%f,%%s}'
		else:
			self.jsonHdr = '{"addr":"%s", "name":"%s", %%s}'
		self.jsonHdr %= (self.host[0], self.hostname)

		with multiprocessing.pool.ThreadPool(3) as pool:
			try:
				waitables = []

				if self.conf.SCAN:
					waitables.append(pool.apply_async(self.portscanloop, (), error_callback=utils.error))
				if self.conf.TRACE:
					waitables.append(pool.apply_async(self.traceloop, (), error_callback=utils.error))

				if self.conf.PING:
					waitables.append(pool.apply_async(self.pingloop, (), error_callback=utils.error))

				for waitable in waitables:
					waitable.wait()

			except KeyboardInterrupt:
				pass
			except Exception as e:
				utils.error(e, 1)

	def pingloop(self):
		"""
		Runs a loop for collecting ping statistics as specified in the
		configuration.
		"""
		printFunc = self.printJSONPing if self.conf.JSON else self.printPing
		try:
			with multiprocessing.pool.ThreadPool() as pool:
				while True:
					self.ping(pool)
					printFunc()
					time.sleep(self.conf.PING / 1000)
		except KeyboardInterrupt:
			pass

	def traceloop(self):
		"""
		Runs a loop for the route traces specified in the configuration
		"""
		printFunc = self.printJSONTrace if self.conf.JSON else self.printTrace
		try:
			while True:
				result = traceroute.trace(self.host, self.ID, self.conf)
				if self.trace != result:
					self.trace = result
					printFunc(result)

				time.sleep(self.conf.TRACE / 1000)
		except KeyboardInterrupt:
			pass

	def portscanloop(self):
		"""
		Runs a loop for port scanning.
		"""
		printFunc = self.printJSONScan if self.conf.JSON else self.printScan
		try:
			with multiprocessing.pool.ThreadPool(3) as pool:
				while True:
					printFunc(ports.portScan(self.host, pool))
					time.sleep(self.conf.SCAN / 1000)
		except KeyboardInterrupt:
			pass

	def printPing(self):
		"""
		Prints a ping result, in plaintext
		"""
		if self.conf.TIMESTAMP:
			print(self.plaintextHdr, time.ctime(), str(self.result[0]), sep='\n', flush=True)
		else:
			print(self.plaintextHdr, str(self.result[0]), sep='\n', flush=True)

	def printJSONPing(self):
		"""
		Prints a ping result, in JSON
		"""
		if self.conf.TIMESTAMP:
			print(self.jsonHdr % (time.time() * 1000, '"ping":' + repr(self.result[0])), flush=True)
		else:
			print(self.jsonHdr % ('"ping":' + repr(self.result[0])), flush=True)

	def printTrace(self, trace:utils.Trace):
		"""
		Prints a route trace, in plaintext
		"""
		if self.conf.TIMESTAMP:
			print(self.plaintextHdr, time.ctime(), utils.traceToStr(trace), sep='\n', flush=True)
		else:
			print(self.plaintextHdr, utils.traceToStr(trace), sep='\n', flush=True)

	def printJSONTrace(self, trace:utils.Trace):
		"""
		prints a route trace, in JSON
		"""
		if self.conf.TIMESTAMP:
			print(self.jsonHdr % (time.time() * 1000, '"trace":' + utils.traceRepr(trace)), flush=True)
		else:
			print(self.jsonHdr % ('"trace":' + utils.traceRepr(trace)), flush=True)

	def printScan(self, scan:utils.ScanResult):
		"""
		Prints a port scan, in plaintext
		"""
		if self.conf.TIMESTAMP:
			print(self.plaintextHdr, time.ctime(), str(scan), sep='\n', flush=True)
		else:
			print(self.plaintextHdr, str(scan), sep='\n', flush=True)

	def printJSONScan(self, scan:utils.ScanResult):
		"""
		Prints a port scan, in JSON
		"""
		if self.conf.TIMESTAMP:
			print(self.jsonHdr % (time.time() * 1000, '"scan":' + repr(scan)), flush=True)
		else:
			print(self.jsonHdr % ('"scan":' + repr(scan)), flush=True)

collectors, confFile = [], None

def hangup(unused_sig: int, unused_frame: object):
	"""
	Handles the SIGHUP signal by re-reading conf files (if available) and resuming execution
	"""
	global confFile, collectors

	# Signal to the threads to stop
	for collector in collectors:
		collector.pipe[0].send(True)

	# Wait for the threads to exit
	for collector in collectors:
		collector.join()

	# Re-read the input file if exists
	# If it doesn't, print an error and go about your business
	if not confFile:
		utils.error(IOError("No input file to read! (input given on stdin)"))
	else:
		readConf()

	for collector in collectors:
		collector.start()

	raise ContinueException()

def terminate(unused_sig: int, unused_frame: object):
	"""
	Handles the SIGTERM signal by cleaning up resources and flushing output pipes.
	"""
	global collectors

	# signal to the  threads to stop
	for c in collectors:
		if c is not None:
			c.terminate()

	# wait for the threads to exit
	for c in collectors:
		if c is not None:
			c.join()

	raise KeyboardInterrupt

def main() -> int:
	"""
	Runs the main routine, returning an exit status indicating successful termination
	"""
	global confFile, collectors

	signal.signal(signal.SIGHUP, hangup)
	signal.signal(signal.SIGTERM, terminate)

	# Construct a persistent monitor based on argv
	if len(sys.argv) > 1:
		confFile = sys.argv[1]

	readConf()

	# Start the collectors
	for c in collectors:
		c.start()

	# The main thread just checks to see that all of the sub-threads are still going, and handles
	# exceptions.
	try:
		while True:
			try:
				time.sleep(5)
				if not collectors or not any(c.is_alive() for c in collectors):
					return 1
			except ContinueException:
				pass

	except KeyboardInterrupt:
		for c in collectors:
			c.pipe[0].send(True)
		for c in collectors:
			c.join()
	except Exception as e:
		utils.error(e)
		return 1
	return 0

def readConf():
	"""
	Reads a configuration file. Expects a file object, which can be a true
	file or a pipe such as stdin
	"""
	global collectors, confFile, config

	# Try to open config file if exists, fatal error if file pointed to
	# Does not/no longer exist(s)
	if confFile:
		try:
			file = open(confFile)
		except OSError as e:
			utils.error(FileNotFoundError("Couldn't read input file '%s'"%e), fatal=True)
		hosts = file.readlines()
		file.close()

	# Closing stdin can cause huge problems, esp. for e.g. debuggers
	else:
		hosts = sys.stdin.readlines()

	# You need to clear this, or the monitor will keep querying old hosts.
	collectors = []

	#parse args
	for i,host in enumerate(hosts):
		args = host.split()
		host = args.pop(0)
		addrinfo = utils.getaddr(host)
		if not addrinfo:
			utils.error(Exception("Unable to resolve host ( %s )" % host))
			sys.stderr.flush()
			continue

		conf = {"HOSTS": {host: addrinfo}}
		try:
			for arg, value in [a.upper().split('=') for a in args]:
				conf[arg] = config[arg](value)
		except ValueError as e:
			utils.error(IOError("Error parsing value for %s: %s" % (arg,e)), True)
		except KeyError as e:
			utils.error(IOError("Error in config file - unknown option '%s'" % arg), True)

		collectors.append(Collector(host, i+1, Config(**conf)))

	if not collectors:
		utils.error(Exception("No hosts could be parsed!"), fatal=True)

class ContinueException(Exception):
	"""
	An exception whose only purpose is to tell the main thread to continue execution
	"""
	pass
