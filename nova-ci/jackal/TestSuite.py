import logging as log
from LoggedProcess import LoggedProcess

class TestSuite(LoggedProcess):
    def __init__(self, test_name, test_config, nova_config, kernel_config, runner, timeout):
        super(TestSuite, self).__init__(timeout)
        self.test_config = test_config
        self.kernel_config = kernel_config
        self.nova_config = nova_config
        self.test_name = test_name
        self.junit = None
        self.runner = runner


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
        pass


    def skipped(self, name):
        return ""

    def success(self, name):
        a = name.split("/")
        return """<testcase classname="{test_class}" name="{name}">
        </testcase>""".format(test_class=self.compute_test_classname(name),
                              name=self.compute_test_name(name))

    def failure(self, name, kind, reason):
        a = name.split("/")
        return """<testcase classname="{test_class}" name="{name}">
                     <failure type="{type}"><![CDATA[{reason}]]></failure>
                  </testcase>""".format(test_class=self.compute_test_classname(name),
                                        name=self.compute_test_name(name),
                                        type=kind,
                                        reason=reason)

    def finish(self):
        LoggedProcess.finish(self)
        self.build_junit()
        log.info(self.log.getvalue())
        log.info(self.junit)
