from LoggedProcess import LoggedProcess
import logging as log
import re
import subprocess

class DMesgDumper(object):
    def __init__(self, filename, hostname):
        self.file = open(filename, "w")
        cmd = "/usr/bin/ssh {} dmesg -w".format(hostname).split(" ")
        self.proc = subprocess.Popen(cmd, stdout=self.file, stderr=self.file)
        
    def done(self):
        self.proc.kill()
        self.file.close()
        
class Dmesg(LoggedProcess):
    def __init__(self, host):
        super(Dmesg, self).__init__("/usr/bin/ssh {} dmesg -w".format(host).split(" "), None)
        self.test_map = {}
        self.last_test = None
        

    def split_log(self):

        if hasattr(self.log.getvalue):
            l = self.log.getvalue()

            c = ""
            name = None
            #log.info("============ DMESG =============")
            for line in l.split("\n"):
                #log.debug(line)
                m = re.search("run fstests (\w+\/\d+)", line);
                if m:
                    if c:
                        self.test_map[name] = c
                        c = ""
                    name = m.group(1)
                c = c + line+"\n"
            if c and name:
                self.test_map[name] = c
        else:
            self.test_map = {}
                
