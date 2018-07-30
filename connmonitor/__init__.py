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
A tool that persistently monitors network conditions with respect to a set of specific hosts
"""

__author__ = "Brennan W. Fieck"

__version__ = "4.0.0"

import sys

def main():
	"""
	Runs the main connmonitor script
	"""
	if len(sys.argv) > 1 and sys.argv[1] in {'-V', '--version'}:
		print("connmonitor Version %s" % __version__)
		exit()

	import connvitals.config
	from .connmonitor import main as main_func
	try:
		return main_func()
	except KeyboardInterrupt:
		return 1
