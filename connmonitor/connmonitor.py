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

collectors, confFile, SLEEP, printFunc = [], None, -1, lambda x: print(x, flush=True)

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


	def loopedRun(self: 'collector.Collector'):
		"""
		This function replaces `Collector.run`, by simply calling the old `.run` repeatedly
		"""
		global printFunc, SLEEP, collector


		with multiprocessing.pool.ThreadPool() as pool:
			try:
				while True:
					time.sleep(SLEEP / 1000)

					if config.PORTSCAN:
						pscanResult = pool.apply_async(ports.portScan,
													   (self.host, pool),
													   error_callback = utils.error)
					if config.TRACE:
						traceResult = pool.apply_async(traceroute.trace,
													   (self.host,),
													   error_callback = utils.error)

					if not config.NOPING:
						try:
							self.ping(pool)
						except (multiprocessing.TimeoutError, ValueError):
							self.result[0] = type(self).result[0]
					if config.TRACE:
						try:
							self.result[1] = traceResult.get(config.HOPS)
						except multiprocessing.TimeoutError:
							self.result[1] = type(self).result[1]
					if config.PORTSCAN:
						try:
							self.result[2] = pscanResult.get(0.5)
						except multiprocessing.TimeoutError:
							self.result[2] = type(self).result[2]

					printFunc(self)
			except KeyboardInterrupt:
				pass
			except Exception as e:
				utils.error(e, 1)

	# Replace Collector.run
	collector.Collector.run = loopedRun

	# Start the collectors
	for c in collectors:
		c.start()

	# The main thread just checks to see that all of the sub-threads are still going, and handles
	# exceptions.
	try:
		while True:
			try:
				time.sleep(0.5)
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
		hosts = file.read().strip().split("\n")
		file.close()

	# Closing stdin can cause huge problems, esp. for e.g. debuggers
	else:
		hosts = sys.stdin.read().strip().split("\n")

	# You need to clear this, or the monitor will keep querying old hosts.
	collectors = []

	#parse args
	try:
		args = [int(arg) for arg in hosts.pop(0).strip().split(" ")]
		config.NOPING   = args[0] == 0
		config.TRACE    = args[1] != 0
		config.PORTSCAN = args[2] != 0
		config.NUMPINGS = args[3]
		config.PAYLOAD  = args[4]
		config.HOPS     = args[5]
		config.JSON     = args[6] != 0
		SLEEP           = args[7]
	except (IndexError, ValueError) as e:
		utils.error(IOError("Bad configuration file format, caused error: (%s)" % e), True)

	if config.JSON:
		printFunc = lambda x: print(repr(x), flush=True)

	#collect host names and valid ip addresses
	for host in hosts:
		addrinfo = utils.getaddr(host)
		if not addrinfo:
			utils.error(Exception("Unable to resolve host ( %s )" % host))
			sys.stderr.flush()
		else:
			config.HOSTS[host] = addrinfo
			collectors.append(collector.Collector(host))

	if not config.HOSTS:
		utils.error(Exception("No hosts could be parsed!"), fatal=True)

class ContinueException(Exception):
	"""
	An exception whose only purpose is to tell the main thread to continue execution
	"""
	pass
