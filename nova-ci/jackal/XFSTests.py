from LoggedProcess import LoggedProcess
import re
from JackalException import *
import logging as log
import DMesg

class XFSTests(LoggedProcess):
    def __init__(self, test_name, test_config, nova_config, kernel_config, runner):
        super(XFSTests, self).__init__(30*60)
        self.test_config = test_config
        self.kernel_config = kernel_config
        self.nova_config = nova_config
        self.test_name = test_name
        self.junit = None
        self.runner = runner
        self.cmd = "/usr/bin/ssh {} nova-testscripts/nova-ci/run.sh run-test xfstests {}".format(runner.get_hostname(), " ".join(self.test_config.tests)).split(" ")


    def compute_test_classname(self, name):
        return self.test_config.name

    def compute_test_name(self, name):
        return "/".join([self.kernel_config.name,
                         self.test_config.name,
                         name,
                         self.nova_config.name])

    def compute_testsuite_name(self):
        return "/".join([self.kernel_config.name,
                         self.nova_config.name,
                         self.test_config.name])
    
    def build_junit(self):
        
        lines = self.log.getvalue().split("\n")

        l = 0
        max_l = len(lines)
        
        def skipped(name):
            return ""
        
        def success(name):
            a = name.split("/")
            return """<testcase classname="{}" name="{}">
</testcase>""".format(a[0], 
                    a[1])
        
        def failure(name, kind, reason):
            a = name.split("/")
            return """<testcase classname="{test_class}" name="{name}">
                         <failure type="{type}"><![CDATA[{reason}]]></failure>
                      </testcase>""".format(test_class=self.compute_test_classname(name),
                                            name=self.compute_test_name(name),
                                            type=kind,
                                            reason=reason)

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

        self.junit =  """<testsuite name="{test_name}" tests="{count}">{tests}</testsuite>""".format(test_name=self.compute_testsuite_name(), count=len(out), tests='\n'.join(out))

    def finish(self):
        LoggedProcess.finish(self)
        self.build_junit()
        print self.junit
