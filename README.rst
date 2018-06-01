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

    1 1 1 10 41 40 1 500
    localhost

The monitor service does **not** check for filesystem updates to that
config file; if you wish to edit it you may safely do so, but should run
``systemctl reload connmonitor`` to read in the new configuration.

Input Format
~~~~~~~~~~~~

connmonitor expects input formatted like this:

::

    DOPINGS DOTRACE DOPSCAN NUMPINGS PAYLOAD HOPS JSON SLEEP
    host1
    host2
    host3
    ...

where the fields have the following meanings

-  ``DOPINGS`` is either ``0`` to indicate that pings should not be
   sent, or any other integer (typically ``1``) to indicate that they
   should be sent.
-  ``DOTRACE`` is either ``0`` to indicate that route tracing should not
   be done, or any other integer (typically ``1``) to indicate they
   should be done.
-  ``DOPSCAN`` is either ``0`` to indicate that port scanning should not
   be done, or any other integer (typically ``1``) to indicate they
   should be done.
-  ``NUMPINGS`` is a positive integer indicating the number of pings to
   be sent. If ``DOPINGS`` is ``0``, this is not used, but **must still
   be specified**. Note that - in general - setting ``NUMPINGS`` to
   ``0`` is less efficient than setting ``DOPINGS`` to ``0``.
-  ``PAYLOAD`` is a positive integer indicating the size of each *ping*
   payload. If ``DOPINGS`` is ``0``, this is not used, but **must still
   be specified**. It is recommended that this be at least 14.
-  ``HOPS`` is a positive integer that sets the maximum number of
   network hops to be considered in route tracing. If ``DOTRACE`` is
   ``0``, this is not used, but **must still be specified**. It is
   recommended that this be at least 15 for testing hosts that are not
   on LAN. Note that - in general - setting ``HOPS`` to ``0`` is less
   efficient than setting ``DOTRACE`` to ``0``.
-  ``JSON`` is either ``0`` to indicate that output should not be
   formatted as JSON, or any other integer (typically ``1``) to indicate
   that output *should* be formatted as JSON.
-  ``SLEEP`` is the amount of time for the process to "sleep" between
   queries of its hosts (in milliseconds).

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

Example
~~~~~~~

Here's an example of a configuration file that will gather port scans
and ping statistics for 10 pings per run each having a payload of 1337B
- but not route traces - from google.com, github.com and the address
127.0.0.1 (localhost) every half-second and outputs in connvitals's
standard, plain-text format:

::

    1 0 1 10 1337 100 0 500
    google.com
    github.com
    127.0.0.1

.. |License| image:: https://img.shields.io/badge/License-Apache%202.0-blue.svg
   :target: https://opensource.org/licenses/Apache-2.0
