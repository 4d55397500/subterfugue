# abstraction for process memory

#	$Header$

from StringIO import StringIO

import errno
import os
import ptrace

_allmemory = {}

def getMemory(pid):
    if not _allmemory.has_key(pid):
        _allmemory[pid] = Memory23(pid)
    return _allmemory[pid]

class Memory:
    def __init__(self, pid):
        self.save = []
        self.pid = pid
        self._areas = None
        
    def peek(self, address, size):
        """read 'size' bytes of data from memory starting at 'address'"""
	pass

    def get_string(self, address):
        """read a null-terminated string starting at 'address'.

	(Note this is awfully slow default implementation.)"""
        s = StringIO()
        while 1:
            c = self.peek(address, 1)[0]
	    address = address + 1
            if ord(c) == 0:
                break
            s.write(c)
        return s.getvalue()

    def poke(self, address, data, fortrick=None):
        """Poke 'data' into 'address'.  If 'fortrick' is not None, this is a
        momentary poke to be popped after syscall return.

        BEWARE: poke and pop are dangerous for child processes which share
        (writable) memory.  This would include any that use clone (e.g. native
        thread programs).  See INTERNALS for more details and the scratch
        module for a better approach.
        """

    def pop(self, fortrick):
        """Pop any momentary pokes that were done for this trick."""
        while self.save and self.save[0][0] == fortrick:
            trick, address, data = self.save.pop(0)
            self.poke(address, data)

    def empty(self):
        "true iff all momentary pokes have been popped"
        return not self.save

    def areas(self, recalculate=0):
        """Returns list of 2-tuples, one for each writable, private area.
        Each 2-tuple contains the start address and length of an area."""
        if not self._areas or recalculate:
            f = open("/proc/%s/maps" % self.pid)
            ms = f.readlines()
            # 08134000-0830f000 rw-p 000eb000 16:01 230682     /usr/bin/emacs-20.5            
            # 0         0         0         0         0         0         0
            ms = filter(lambda s: s[19] == 'w' and s[21] == 'p', ms)
            self._areas = map(convert_area, ms)
        return self._areas

class Memory23(Memory):
    def __init__(self, pid):
	"""This uses /proc/PID/mem to access tracee's memory. That is
	fast, but only works on 2.3.X kernels. It could be even faster if we
	mmap'd /proc/PID/mem"""
	Memory.__init__(self, pid)
        # XXX: maybe the open should be lazy?
        # FIX: what if /proc missing?
        self.m = os.open("/proc/%s/mem" % pid, os.O_RDWR)
        
    def peek(self, address, size):
        _memseek(self.m, address)
        s = os.read(self.m, size)
        if len(s) < size:
            raise IOError, 'short read'
        return s

    def get_string(self, address):
        s = StringIO()
        _memseek(self.m, address)
        while 1:
            # XXX: do something better here
            # (don't just use buffered read, though, because there is some bad
            # interaction with read/seek on /proc/n/mem)  (glibc bug?)
            c = os.read(self.m, 1)[0]
            if ord(c) == 0:
                break
            s.write(c)
        return s.getvalue()

    def poke(self, address, data, fortrick=None):
        if fortrick:
            self.save.insert(0, (fortrick, address,
                                 self.peek(address, len(data))))
            # XXX: could check whether poke is a noop here
        _memseek(self.m, address)
        r = os.write(self.m, data)
        assert r == len(data)           # FIX

class Memory22(Memory):
    def __init__(self, pid):
	"""This is slow version of memory object, which works on 2.2.X kernels."""
	Memory.__init__(self, pid)

    def readbyte(self, address):
	"""Read one byte (ptrace allows us to read word, only). This needs to be
	changed for non-i386."""
	word = ptrace.peekdata(self.pid, address & ~3)
	i = address & 3
	if i == 0: return word          & 0xff
	if i == 1: return (word >> 8)   & 0xff
	if i == 2: return (word >> 16)  & 0xff
	if i == 3: return (word >> 24)  & 0xff
	assert 0, "This can not happen"
        
    def peek(self, address, size):
        "read 'size' bytes of data from memory starting at 'address'"

	print "Peeking %d bytes of data at %d" % (size, address)
        s = StringIO()
	for i in range(size):
	    c = self.readbyte(address+i)
	    print "Got char %c" % c
	    s.write(chr(c))
        return s.getvalue()

    def poke(self, address, data, fortrick=None):
	assert 0, "Not yet implemented"

def convert_area(s):
    start = _xtoi(s, 0)
    end = _xtoi(s, 9)
    return (start, end - start)

def _xtoi(s, offset):
    return eval('0x' + s[offset:offset+8])


def _memseek(f, address):
    "seek in /proc/<n>/mem using signed address"
    if address >= 0:
        r = os.lseek(f, address, 0)
        assert r == address
    else:
        # XXX: ugh--expose llseek to python and/or fix mem's size so it can
        # seek backward from EOF
        r = os.lseek(f, 0x7fffffff, 0)
        assert r == 0x7fffffff
        try:
            os.lseek(f, 0x7fffffff, 1)
        except OSError, e:
            if e.errno != errno.EOVERFLOW:
                raise
        try:
            os.lseek(f, address + 2, 1)
        except OSError, e:
            if e.errno != errno.EOVERFLOW:
                raise

