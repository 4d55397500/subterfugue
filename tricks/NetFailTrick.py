# make client net connections fail

#       Copyright 2000 Mike Coleman <mkc@subterfugue.org>
#       Can be freely distributed and used under the terms of the GNU GPL.


#	$Header$

from Trick import Trick

import errno

class NetFail(Trick):
    def usage(self):
        return """
        Causes calls to connect to fail with error EHOSTUNREACH, and calls to
        listen to fail with EOPNOTSUPP.
"""
    
    def __init__(self, options):
        self.options = options

    def callbefore(self, pid, call, args):
        assert call == 'socketcall'

        subcall = args[0]
        if subcall == 3:                # connect
            return (None, -errno.EHOSTUNREACH, None, None)
        if subcall == 4:                # listen
            return (None, -errno.EOPNOTSUPP, None, None)
        else:
            return (subcall, None, None, None)

    def callafter(self, pid, call, result, state):
        assert call == 'socketcall'
        assert state != 3 and state != 4

    def callmask(self):
        # in older kernels, there was a pre-socketcall syscall 'connect',
        # but assume here that it won't be present in kernels we'll see
        return { 'socketcall' : 1 }
