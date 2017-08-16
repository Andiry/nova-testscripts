from LoggedProcess import LoggedProcess
import re
from JackalException import *
import logging as log
import DMesg
import tempfile

import TestSuite

class LTP(TestSuite.TestSuite):
    def __init__(self, test_name, test_config, nova_config, kernel_config, runner):
        super(LTP, self).__init__(test_name, test_config, nova_config, kernel_config, runner, 30*60)
        self.cmd = "/usr/bin/ssh {host} nova-testscripts/nova-ci/run.sh run-test ltp {args}".format(host=runner.get_hostname(), args=test_config.config).split(" ")

    def build_junit(self):
        lines = self.log.getvalue().split("\n")
        l = 0
        max_l = len(lines)
        out = []

        while l < max_l:
            g = re.search("(^\S+)\s+(\d+)\s+T(PASS|FAIL)\s*:\s*(.*)", lines[l])
            if g:
                name="{}-{}".format(g.group(1), g.group(2))
                if g.group(3) == "PASS":
                    out.append(self.success(name))
                else:
                    out.append(self.failure(name, g.group(3), g.group(4)))

            l += 1
            
        self.junit= """<testsuite name="{test_name}"  tests="{count}">
        {tests}
        </testsuite>
        """.format(test_name=self.compute_testsuite_name(), count=len(out), tests='\n'.join(out))

    
