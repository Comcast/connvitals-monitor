connvitals-monitor
==================

|License|

Persistently monitors network conditions with respect to a set of
specific hosts.

Dependencies
------------

The executable for the connvitals-monitor package (``connmonitor``) runs
on python3 (tested CPython 3.6.3) and requires a python3 interpreter. It
also requires ```connvitals`` <https://github.com/comcast/connvitals>`__
to exist as a subdirectory in its directory (or your ``import`` path) as
it uses that as a library.

*Note: Because this package is not in a standard repository (nor is its
dependency), dependencies cannot be automatically resolved; you must
first install connvitals for this package to work.*

Installation
------------

    *Note: Versions 1.2+ **only** support Linux systems that run
    systemd. It's possible that it may install on your system even if
    you do not run systemd, but it will attempt to install the Unit File
    under ``/usr/lib/systemd/system``.*

Via ``pip`` (Standard)
~~~~~~~~~~~~~~~~~~~~~~

By far the easiest way to install connvitals-monitor is to simply use
``pip`` like so:

::

    pip install connmonitor

Note that you'll probably need to run this command with ``sudo`` or the
``--user`` flag.

Via ``pip`` (From This Repository)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The easiest way to install is to simply use ``pip``. You can install
directly from this repository without needing to manually download it by
running

.. code:: bash

    user@hostname ~ $ pip install git+https://github.com/comcast/connvitals-monitor.git#egg=connmonitor

Note that you may need to run this command as root/with ``sudo`` or with
``--user``, depending on your ``pip`` installation. Also ensure that
``pip`` is installing packages for Python 3.x. Typically, if both
Python2 and Python3 exist on a system with ``pip`` installed for both,
the ``pip`` to use for Python3 packages is accessible as ``pip3``.

Manually
~~~~~~~~

To install manually, first download or clone this repository. Then, in
the directory you downloaded/cloned it into, run the command

.. code:: bash

    user@hostname ~/connvitals-monitor $ python setup.py install

| Note that it's highly likely that you will need to run this command as
  root/with ``sudo``. Also ensure that the ``python`` command points to
  a valid Python3 interpreter (you can check with ``python --version``).
  On many systems, it is common for ``python`` to point to a Python2
  interpreter. If you have both Python3 and Python2 installed, it's
  common that they be accessible as ``python3`` and ``python2``,
  respectively.
| Finally, if you are choosing this option because you do not have a
  Python3 ``pip`` installation, you may not have ``setuptools``
  installed. On most 'nix distros, this can be installed without
  installing ``pip`` by running
  ``sudo apt-get install python3-setuptools`` (Debian/Ubuntu),
  ``sudo pacman -S python3-setuptools`` (Arch),
  ``sudo yum install python3-setuptools`` (RedHat/Fedora/CentOS), or
  ``brew install python3-setuptools`` (macOS with ``brew`` installed).

Usage
-----

.. code:: bash

    $ connmonitor [input file]
    $ connmonitor [ -v --version ]

| ``input file`` is a file containing a set of options and hosts to
  check. If not specified, ``connmonitor`` will read input of the same
  format from ``stdin``. If instead ``-v`` or ``--version`` is passed as
  the first argument, the program's version is printed to stdout, and
  the program exits successfully.
| Upon receiving ``SIGHUP`` (e.g. when the terminal used to run it is
  closed), ``connmonitor`` will attempt to re-read its configuration
  file, then continue execution. If the configuration file cannot be
  read, the program will log an error, clean up its resources and exit
  with error code ``1``. If input was given on ``stdin``, the program
  will log an error and resume execution.
| ``connmonitor`` handles ``SIGTERM`` by neatly cleaning up resources
  (finishing any running tasks and printing their output to ``stdout``,
  still logging any errors) and exiting.

As a ``systemd`` daemon
~~~~~~~~~~~~~~~~~~~~~~~

Starting with version 1.2.1, connvitals-monitor (unfortunately) comes
packaged with a systemd Unit File, and will attempt to install it. To
run the daemon, simply run ``systemctl start connmonitor`` (as root),
and to stop it run ``systemctl stop connmonitor`` (also as root). By
default, the monitor will log its ``stdout`` in JSON format to
``/var/log/connmonitor.log``, and its ``stderr`` to
``/var/log/connmonitor.err``. Whenever the monitor is started, it looks
for a configuration file at ``/var/run/connmonitor.conf``, and creates
it if it does not exist with the following default contents (see 'Input
Format'):

::

    localhost trace=5000 scan=5000 json=True

The monitor service does **not** check for filesystem updates to that
config file; if you wish to edit it you may safely do so, but should run
``systemctl reload connmonitor`` to read in the new configuration.

Input Format
~~~~~~~~~~~~

connmonitor expects input formatted like this:

::

    host1 ping=500 trace=30000 hops=40 scan=60000 json=1
    host2 ping=50 numpings=10 payload=41
    host3 trace=1000 hops=10
    ...

Note that config lines (except the hostname part, when applicable) are
cAsE-iNsEnSiTiVe. Empty lines are ignored at any point.

| Each line of the config *must* begin with a host. This can be either
  an IP address or a Fully-Qualified Domain Name (FQDN). Currently, IPv6
  is not supported, and if an FQDN can only be resolved to an IPv6
  address it will not be queried.
| After the host, a list of options in the format ``<name>=<value>`` can
  be specified. If an option is not specified, a default value is used.
  The options and their valid values are:

-  ``ping`` - can be set to any positive, rational number or 0 (zero).
   This indicates the frequency at which pings are performed by
   specifying a duration (in milliseconds) to wait between each burst of
   pings. A value of 0 indicates that pings should not be sent. Default:
   500
-  ``numpings`` - can be set to any positive integer. Indicates the
   number of pings that should be sent in a "burst". Default: 10
-  ``payload`` - can be set to any positive integer. This indicates the
   size in bytes of a payload to be sent with each ping. Typically, this
   will have little to no impact on ping results, but can, in some
   networks/situations diagnose specific issues. Default: 41
-  ``trace`` - can be set to any positive, rational number or 0 (zero).
   This indicates the frequency at which route traces are done by
   specifying a duration (in milliseconds) to wait between each route
   trace. A new route trace will not begin until the previous one has
   finished, so setting this to values lower than network latency to the
   target is typically meaningless. A value of 0 (zero) indicates that
   route traces should not be performed. Default: 0 (zero)
-  ``hops`` - can be set to any positive integer. This indicates the
   number of network hops to be used as an upper limit on route traces.
   The default value typically suffices in most situations. Default: 30
-  ``scan`` - can be set to any positive, rational number or 0 (zero).
   This indicates the frequency at which route traces are done by
   specifying a duration (in milliseconds) to wait between each port
   scan. A value of 0 (zero) indicates that port scans should not be
   done. Default: 0 (zero)
-  ``json`` - can be set to any integer or 0 (zero), *or* one of the
   Python boolean constants: ``True`` and ``False``. If this value is
   any non-zero integer or ``True``, then the output of this host's
   statistics will be in JSON format rather than the plain-text format.
   Default: ``False``
-  ``timestamp`` - can be set to any integer or 0 (zero), *or* one of
   the Python boolean constants: ``True`` and ``False``. If this value
   is any non-zero integer or ``True``, then the outputs of this hosts's
   statistics will always contain timestamps indicating the time at
   which printing occurs. Default: ``True``

Configuration options can appear in any order and can be separated by
any amount/kind of whitespace except for line terminators (Line Feed,
Carriage Return, Form Feed etc.). However, the same option *cannot* be
specified multiple times on the same line, even if it always appears
with the same value. Furthermore, there must be no space on either side
of the ``=`` assigning a value to a config variable.

Output Format
~~~~~~~~~~~~~

``connmonitor`` outputs results to ``stdout`` and logs errors to
``stderr``. Output (including JSON output) takes the same form as
connvitals, and you can read about that format on `that
project <https://github.com/comcast/connvitals>`__'s README.

Starting with version 3.0, ``connmonitor`` will no longer output traces
if they are determined to be the same as the most recent route
previously recorded for a given host. This is as a result of changes
made to connvitals (but only the Python version) which are discussed in
greater detail on `that project's
page <https://github.com/comcast/connvitals>`__.

Starting with version 3.1, ``connmonitor`` will output a timestamp as a
part of the JSON object (a floating-point number in milliseconds since
the UNIX Epoch), and will output a human-readable date and time in the
plaintext output on the second line (directly after names/IP addresses)
in the system's ``ctime`` format. All timestamps are given in the
timezone for which the system is configured.

Starting with version 4.0, each statistic is reported individually, and
not bundled together the way ``connvitals`` outputs them. This
essentially looks like a separate output for each statistic, as though
each were invoked seperately by a different ``connvitals`` invokation.
Prior to this version, configurations were global and all statistics
were gathered at the same frequency.

Example
~~~~~~~

Here's an example of a configuration file that will gather port scans
and ping statistics for 10 pings per run each having a payload of 1337B
- but not route traces - from google.com every half-second with output
in ``connvitals``'s standard, plain-text output, and do limited port
scanning and traceroutes (to a maximum of 30 hops) - but not pings - on
the address 127.0.0.1 (localhost) every 50 milliseconds with output in
JSON format:

::

    google.com ping=500 payload=1337 scan=500
    127.0.0.1 trace=50 json=1 scan=50

.. |License| image:: https://img.shields.io/badge/License-Apache%202.0-blue.svg
   :target: https://opensource.org/licenses/Apache-2.0
