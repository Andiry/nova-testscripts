import StringIO
import logging as log
from JackalException import *
import sys
import time
import fcntl
import subprocess
import os

class LoggedProcess(object):
    def __init__(self, cmd, timeout=None, outfile=None):
        super(LoggedProcess, self).__init__()
        self.cmd = cmd
        self.task = None
        if outfile is None:
            self.log = StringIO.StringIO()
        else:
            self.log = outfile
            
        self.timeout = timeout
        self.ready_to_finish = False
        #self.finish = False
        if not self.cmd:
            self.cmd = [""]

    def go(self):
        self.start()
        while self.step():pass

    def start(self):
        log.info("Starting {}".format(" ".join(self.cmd)))
        log.debug("Starting {}".format(self.cmd))
        self.proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Make reading stdout non-blocking
        fd = self.proc.stdout.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        self.start = time.clock()

    def step(self):
        if self.ready_to_finish:
            return False
        
        if self.timeout is not None and time.clock() > self.start + self.timeout:
            raise TimeoutException()

        def read_as_must_as_possible():
            while True:
                l = self.proc.stdout.read(1024)
                if not l:
                    break
                self.log.write(l)
                sys.stderr.write(".")
        try:
            # read everything that remains
            read_as_must_as_possible()
        except IOError as e:  # when there's nothing to read, we'll get an exception
            time.sleep(0.1)
        finally:
            if self.proc.poll() is not None: # if the process is dead, there's
                                             # nothing much more coming
                
                read_as_must_as_possible() # read one more time, because more
                                           # data may have shown up.
                log.info("return value: {}".format(self.proc.returncode))
                self.ready_to_finish = True
                return False
            else:                            # otherwise, try again
                return True
            
    def finish(self):
        log.info("Finished: {}".format(self.cmd))
