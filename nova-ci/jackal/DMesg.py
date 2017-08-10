from LoggedProcess import LoggedProcess
import logging as log
import re

class Dmesg(LoggedProcess):
    def __init__(self, host):
        super(Dmesg, self).__init__("/usr/bin/ssh {} dmesg -w".format(host).split(" "), None)
        self.test_map = {}
        self.last_test = None
        

    def split_log(self):
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
                
