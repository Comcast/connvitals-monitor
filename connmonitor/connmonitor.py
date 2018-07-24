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
from connvitals import utils, config, collector, ports, traceroute

class Collector(collector.Collector):
	"""
	The connvitals-monitor collector, that overrides parts of the
	connvitals collector.
	"""

	def run(self):
		"""
		Called when the thread is run
		"""
		global SLEEP

		with multiprocessing.pool.ThreadPool() as pool:
			try:
				while True:
					time.sleep(SLEEP[self.ID] / 1000)

					if self.conf.PORTSCAN:
						pscanResult = pool.apply_async(ports.portScan,
													   (self.host, pool),
													   error_callback = utils.error)
					if self.conf.TRACE:
						traceResult = pool.apply_async(traceroute.trace,
													   (self.host, self.ID, self.conf),
													   error_callback = utils.error)

					if not self.conf.NOPING:
						try:
							self.ping(pool)
						except (multiprocessing.TimeoutError, ValueError):
							self.result[0] = type(self).result[0]
					if self.conf.TRACE:
						try:
							self.result[1] = traceResult.get(self.conf.HOPS)
						except multiprocessing.TimeoutError:
							self.result[1] = type(self).result[1]
					if self.conf.PORTSCAN:
						try:
							self.result[2] = pscanResult.get(0.5)
						except multiprocessing.TimeoutError:
							self.result[2] = type(self).result[2]

					self.print()
			except KeyboardInterrupt:
				pass
			except Exception as e:
				utils.error(e, 1)

	def print(self):
		"""
		Prints this collector, using a method dependent on its configuration
		"""
		if self.conf.JSON:
			print(repr(self))
		else:
			print(self)

	def __str__(self) -> str:
		"""
		Implements `str(self)`

		Returns a plaintext output result
		"""
		ret = []
		if self.host[0] == self.hostname:
			ret.append(self.hostname)
		else:
			ret.append("%s (%s)" % (self.hostname, self.host[0]))

		ret.append(time.ctime())

		pings, trace, scans = self.result

		if pings and not self.conf.NOPING:
			ret.append(str(pings))
		if trace and trace != self.trace and self.conf.TRACE:
			self.trace = trace
			ret.append(str(trace))
		if scans and self.conf.PORTSCAN:
			ret.append(str(scans))

		return "\n".join(ret)

	def __repr__(self) -> repr:
		"""
		Implements `repr(self)`

		Returns a JSON output result
		"""
		ret = [r'{"addr":"%s"' % self.host[0]]
		ret.append(r'"name":"%s"' % self.hostname)

		if not self.conf.NOPING:
			ret.append(r'"ping":%s' % repr(self.result[0]))

		if self.conf.TRACE and self.trace != self.result[1]:
			self.trace = self.result[1]
			ret.append(r'"trace":%s' % repr(self.result[1]))

		if self.conf.PORTSCAN:
			ret.append(r'"scan":%s' % repr(self.result[2]))

		ret.append(r'"timestamp":%f' % (time.time()*1000))

		return ','.join(ret) + '}'


collectors, confFile, SLEEP = [], None, {}

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
				time.sleep(max(SLEEP.values()) / 900)
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
	global collectors, confFile, SLEEP, printFunc

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
		else:
			try:
				args = [int(arg) for arg in args]
				print(args)
				conf = config.Config(NOPING   = args[0] == 0,
				                     TRACE    = args[1] != 0,
				                     PORTSCAN = args[2] != 0,
				                     NUMPINGS = args[3],
				                     PAYLOAD  = args[4],
				                     HOPS     = args[5],
				                     JSON     = args[6] != 0,
				                     HOSTS    = {host: addrinfo})
				SLEEP[i] = args[7]
				collectors.append(Collector(host,i,conf=conf))
			except (IndexError, ValueError) as e:
				utils.error(IOError("Bad configuration file format, caused error: (%s)" % e), True)

	if not SLEEP:
		utils.error(Exception("No hosts could be parsed!"), fatal=True)

class ContinueException(Exception):
	"""
	An exception whose only purpose is to tell the main thread to continue execution
	"""
	pass
