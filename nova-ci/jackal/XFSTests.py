from LoggedProcess import LoggedProcess
import re
from JackalException import *
import logging as log
import DMesg
import tempfile
import TestSuite

class XFSTests(TestSuite.TestSuite):
    def __init__(self, test_name, test_config, nova_config, kernel_config, runner):
        super(XFSTests, self).__init__(test_name, test_config, nova_config, kernel_config, runner, 30*60)
        self.cmd = "/usr/bin/ssh {host} nova-testscripts/nova-ci/run.sh run-test xfstests {args}".format(host=runner.get_hostname(), args=test_config.config).split(" ")

    def build_junit(self):
        
        lines = self.log.getvalue().split("\n")

        l = 0
        max_l = len(lines)
        

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
                    out.append(self.success(test_name))
                elif re.search("^\d+s", lines[l]):
                    out.append(self.success(test_name))
                elif re.search("^- output mismatch", lines[l]) or re.search("^\[failed", lines[l]):
                    error = lines[l]
                    l += 1
                    while l < max_l:
                        if re.search("^    ", lines[l]):
                            error += lines[l][4:] + "\n"
                        else:
                            break
                        l += 1
                    out.append(self.failure(test_name, "failure", error))
                else:
                    assert False
            l += 1

        self.junit =  """<testsuite name="{test_name}" tests="{count}">{tests}</testsuite>""".format(test_name=self.compute_testsuite_name(), count=len(out), tests='\n'.join(out))

