from LoggedProcess import LoggedProcess
import re
from JackalException import *
import logging as log
import DMesg
import tempfile

import TestSuite

class FSTest(TestSuite.TestSuite):
    def __init__(self, test_name, test_config, nova_config, kernel_config, runner):
        super(FSTest, self).__init__(test_name, test_config, nova_config, kernel_config, runner, 30*60)
        self.cmd = "/usr/bin/ssh {host} nova-testscripts/nova-ci/run.sh run-test fstest {args}".format(host=runner.get_hostname(), args=test_config.config).split(" ")

    def build_junit(self):
        self.junit = self.log.getvalue()
        #print self.log.getvalue()
        #/home/swanson/nova-testscripts/nova-ci/fstest/pjd-fstest/tests/chflags/00.t ... ok
        lines = self.log.getvalue().split("\n")
        l = 0
        max_l = len(lines)
        out = []

        while l < max_l:
            g = re.search("^.*/tests/(.*\.t) \.+ (\w+)", lines[l])
            if g:
                if g.group(2) == "ok":
                    out.append(self.success(g.group(1).replace("/","_")))
                else:
                    out.append(self.failure(g.group(1).replace("/","_"), g.group(2), ""))

            l += 1
            
        self.junit= """<testsuite name="{test_name}"  tests="{count}">
        {tests}
        </testsuite>
        """.format(test_name=self.compute_testsuite_name(), count=len(out), tests='\n'.join(out))

    
