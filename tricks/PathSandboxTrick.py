#
#       Interactive, config-file based path sandbox
#
#       Copyright 2000 Pavel Machek <pavel@ucw.cz>
#       Can be freely distributed and used under the terms of the GNU GPL.
#

#	$Header$

from BoxTrick import Box

import copy
import errno
import os
import re
import string
import types
import FCNTL
import posix

import Memory
import tricklib
import fileinput
import re

import signal
import time

answer = 0;

configfile = 'default'

def user_signal(signo, b, trick):
    global configfile
    print 'Rereading config from ', configfile
    if signo == signal.SIGTERM:
        raise 'I was asked to kill my children'
    trick.reconfig(configfile, signo)

def question(q):
    global answer
    answer = 0
    print 'SANDBOX %s' % q
    try:
	time.sleep(3600)
    except IOError:
	pass
    if answer == 0:
	assert 0, 'User failed to respond within one hour'
    print 'User responded with ', answer
    return answer

def readconfig(object, configfile, method, configname):
    for line in fileinput.FileInput(posix.environ['SUBTERFUGUE_ROOT'] + '/conf/' +configfile, 0, ""):
	line = re.sub('\012$', '', line)	# kill cariage return
#	    line = re.sub('\.', '\.', line)
	if re.match('^#.*', line): continue
	if re.match('^include ', line):
	    line = re.sub('^include ', '', line)
	    readconfig(object, line, method, configname)
	    continue

	# Perform environment variable substitution
	while 1:
	    var = re.search('\$[a-zA-Z]+', line)
	    if not var: break
	    var   = line[var.start()+1:var.end()]
	    print 'Should work with variable ', var, ' containing ', posix.environ[var]
	    line = re.sub('\$'+var, posix.environ[var], line)

	if not re.match('^'+configname, line): continue
	line = re.sub('^'+configname+' ', '', line)
	method(line)

class PathSandbox(Box):
    def usage(self):
        return """
        Restricts filesystem access to paths specified by config file.

	Format of config file is as follows:

	path {allow, deny, allow_if_public} {read,write,ask} path

	You are allowed to create lines like this:

	path alllow_if_public read /
	path allow read,write /dev/tty

	On each operation, config is scanned from the beggining to the
	end. If path from config is start of current path,
	access is allowed or denied, and no further processing is
	done. Allow_if_public means that sandbox looks at access mode
	of given object. If is not readable for everyone, file is scanned further
	, otherwise access is allowed.

	Notice that allow_if_public is slightly dangerous:

	application: open /foo/bar
	subterfugue: checks that /foo/bar is readable from other thread
	you: rm /foo/bar; umask 700; echo "secret data" > /foo/bar
	subterfugue: allows access to /foo/bar

	Solution is not using allow_if_public. (Unfortunately,
	allow_if_public that said "denied" on non-existant files is
	not terribly usefull: applications like to open non-existant
	files for example when they search path.)

	names like this. [Notice that if you did chmod instead of
	rm&umask, you'd be in danger even without subterfugue.]

	If you add "allow ask /" line into config file, then "denied"
	accesses are not really denied, but user is prompted whether
	or not he really wants to perform given operation.

	This syntax should be compatible with syntax used in janus.
"""

    def oneline(self, line):
        print 'got line> ', line
	line = re.sub('\\*', '.*', line)	# we want regexp-style stars
	xpath = re.sub('^[a-z_]* [a-z_,]* ', '', line)

	if re.match('^deny', line):            path = '-' + xpath
	if re.match('^allow', line):           path = '+' + xpath
	if re.match('^allow_if_public', line): path = '?' + xpath

	line = re.sub('^[a-z_]* ', '', line)

	if re.match('^[a-z,]*write', line): self._write = [ path ] + self._write
	if re.match('^[a-z,]*read', line):  self._read=   [ path ] + self._read
	if re.match('^[a-z,]*ask', line):   self._ask =   [ path ] + self._ask

    def __init__(self, options):
	global configfile
	Box.__init__(self, options)
	self._quiet = 0
	print 'SANDBOX MYPID ', os.getpid()
	signal.signal(signal.SIGHUP,  lambda a, b, t = self: user_signal(a,b,t))
	signal.signal(signal.SIGTERM, lambda a, b, t = self: user_signal(a,b,t))
	signal.signal(signal.SIGUSR1, lambda a, b, t = self: user_signal(a,b,t))
	signal.signal(signal.SIGUSR2, lambda a, b, t = self: user_signal(a,b,t))
	configfile = options.get('config',configfile)

    def onaccess(self, pid, call, r, op, path):
        followlink = 1 # FIXME
	p = tricklib.canonical_path(pid, path, followlink)
	if r == -1:
	    if self.access(pid, p, followlink, self._ask) != 0:
		return (None, -errno.EACCES, None, None)

	    if question( 'QUESTION (%s): %s %s' % (call, op, p)) == 1:     # Yes (should we use repr(p)? 
		return
	    else:
		return (None, -errno.EACCES, None, None)

        elif r != 0:
            return (None, -r, None, None)

	return 'cont'
            
    def callmask(self):
        return self.callaccess

    def reconfig(self, file, signo):
	global answer
	if signo == signal.SIGUSR1: answer = 1	
	if signo == signal.SIGUSR2: answer = 2

	self._read=[]
	self._write=[]
	self._ask=[]
	readconfig(self, file, self.oneline, "path")

	print 'self._read = ', self._read
	print 'self._write = ', self._write
	print 'self._ask = ', self._ask
