from LoggedProcess import LoggedProcess
import re
from JackalException import *
import logging as log
import DMesg

class XFSTests(LoggedProcess):
    def __init__(self, test_name, tconf, runner):
        super(XFSTests, self).__init__(30*60)
        self.tconf = tconf
        self.test_name = test_name
        self.junit = None
        self.runner = runner
        self.dmesg = None
        self.cmd = "/usr/bin/ssh {} nova-testscripts/nova-ci/run.sh run-test xfstests {}".format(runner.get_hostname(), " ".join(self.tconf.tests)).split(" ")
    
    def build_junit(self, dmesg_map={}):
        
        lines = self.log.getvalue().split("\n")

        l = 0
        max_l = len(lines)
        
        def skipped(name):
            return ""
        
        def success(name):
            a = name.split("/")
            return """<testcase classname="{}" name="{}">
                         <dmesg><![CDATA[{dmesg}]]></dmesg>
<testcase/>""".format(a[0], 
                    a[1], 
                    dmesg=dmesg_map.get(name) or "")
        
        def failure(name, kind, reason):
            a = name.split("/")
            return """<testcase classname="{test_class}" name="{name}">
                         <failure type="{type}"><![CDATA[{reason}]]></failure>
                         <dmesg><![CDATA[{dmesg}]]></dmesg>
                      </testcase>""".format(test_class=a[0], 
                                            name=a[1],
                                            type=kind,
                                            reason=reason,
                                            dmesg=dmesg_map.get(name) or "")

        out = []

        while l < max_l:
            #log.debug(lines[l])
            g = re.search("^(\w+/\d\d\d)\s+", lines[l])
            if g:
                test_name = g.group(1)
                lines[l] = lines[l][len(g.group(0)):]

                if re.search("^\[not run]", lines[l]):
                    pass#out.append(skipped(test_name))
                elif re.search("^\d+s \.\.\. \d+s", lines[l]):
                    out.append(success(test_name))
                elif re.search("^\d+s", lines[l]):
                    out.append(success(test_name))
                elif re.search("^- output mismatch", lines[l]) or re.search("^\[failed", lines[l]):
                    error = lines[l]
                    l += 1
                    while l < max_l:
                        if re.search("^    ", lines[l]):
                            error += lines[l][4:] + "\n"
                        else:
                            break
                        l += 1
                    out.append(failure(test_name, "failure", error))
                else:
                    assert False
            l += 1

        self.junit =  """<testsuite name="{test_name}" tests="{count}">{tests}</testsuite>""".format(test_name=self.test_name, count=len(out), tests='\n'.join(out))

    def start(self):
        self.dmesg = DMesg.Dmesg(self.runner.get_hostname())
        LoggedProcess.start(self)
        self.dmesg.start()

    def step(self):
        
        try:
            return LoggedProcess.step(self) and self.dmesg.step()
        except TimeoutException as e:
            log.error("{} Timed out".format(self.test_name))
            return False
        
    def finish(self):
        LoggedProcess.finish(self)
        self.dmesg.finish()
        self.dmesg.split_log()
        self.build_junit(self.dmesg.test_map)
        print self.junit
