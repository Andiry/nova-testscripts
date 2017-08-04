import argparse
import pexpect
import sys
import re
import time
import logging as log
import StringIO
import subprocess
import fcntl
import os


reboot_timeout=120 # seems to take about a minute, usually.
logout_delay=10

out = None

class Tee(object):
    def __init__(self, fs):
        self.files = fs
    def write(self, data):
        for i in self.files:
            i.write(data)
    def flush(self):
        for i in self.files:
            i.flush()

class Host(object):
    def __init__(self, hostname, prompt, args):
        self.host = hostname
        self.prompt = prompt
        self.args = args

    def exit(self):
        self.ssh.sendline("exit")
        self.ssh.expect(pexpect.EOF)
        
    def test(self, conf):
        self.open_shell()
        self.simple_command("echo hello")
        self.exit()
        self.update_nova_ci()
        self.update_kernel(conf)
        
    def open_shell(self, timeout=None):
        if timeout is None:
            timeout=reboot_timeout
            
        cmd = "/bin/bash ./ssh_retry.sh {}".format(self.host)
        #log.debug(cmd)
        self.ssh = pexpect.spawn(cmd, logfile=out)
        self.ssh.expect(self.prompt, timeout=timeout)
        self.simple_command(". nova-testscripts/nova-ci/remote_funcs.sh")

    def simple_command(self, cmd, timeout=20):
        self.ssh.sendline(cmd)
        self.ssh.expect(self.prompt, timeout=timeout)
        
    def shell_cmd(self, cmd, timeout=20):
        log.info(cmd)
        self.open_shell()
        self.simple_command(cmd, timeout=timeout)
        self.exit()
        
    def update_nova_ci(self):
        self.shell_cmd("update_self")

    def update_kernel(self, nconf):
        self.open_shell()
        self.simple_command("update_kernel {} {} {}".format(nconf.kernel_config_file,
                                                            nconf.kernel_repo[0],
                                                            nconf.kernel_repo[1]))
        self.exit()

    def build_kernel(self):
        self.shell_cmd("build_kernel", timeout=30*60)
        
    def install_kernel(self):
        self.shell_cmd("install_kernel")
        
    def prepare_host_config(self, nconf, reboot=False):
        if reboot:
            self.reboot_to_nova()
        self.update_nova_ci()
        self.update_kernel(nconf)
        if not self.args.no_rebuild_kernel:
            self.build_kernel()
            self.install_kernel()
        #self.reboot_to_nova(force=True)

    def hard_reboot(self):
        log.info("Hard rebooting...")
        raise NotImplemented()

    def load_nova(self, nconf):
        log.info("Loading nova...")
        self.shell_cmd("load_nova {}".format(nconf.module_args))
        self.shell_cmd("list_module_args nova")
        
    def reset_host(self, nconf):
        if not self.soft_reboot():
            self.hard_reboot()
        self.reboot_to_nova()
        
    def soft_reboot(self):
        log.info("Soft rebooting...")
        try:
            self.open_shell(timeout=10)
            self.ssh.sendline("sudo systemctl reboot -i")
            self.ssh.expect(pexpect.EOF)
            time.sleep(5)
            log.info("logging in...")
            self.open_shell(timeout=reboot_timeout)
            self.exit()
            return True
        except Exception as e:
            log.error("Couldn't soft reboot: {}".format(e))
            return False
        
    def reboot_to_nova(self, retry=True, force=False):
        log.info("Checking kernel version on {}".format(self.host))
        self.open_shell()
        self.ssh.sendline("uname -a")
        t = self.ssh.expect(["-nova",
                        "-generic"])
        if t == 0 and not force:
            log.info("Found nova kernel")
            return
        else:
            if force:
                log.info("Forced reboot")
            else:
                log.info("Found non-nova kernel")
                
            if retry:
                log.info("Rebooting...")
                self.ssh.sendline("reboot_to_nova & exit")
                self.ssh.expect(pexpect.EOF)
                time.sleep(logout_delay)
                self.reboot_to_nova(retry=False)
            else:
                log.info("Giving up.")
                raise Exception("Couldn't reboot to nova")

    def prepare_pmem(self):
        log.info("Looking for pmem devices...")
        failures = 0
        while failures < 10:
            self.open_shell()
            try:
                self.ssh.sendline("check_pmem")
                r = self.ssh.expect(["ok",
                                     "missing"])
                if r == 0:
                    log.info("Found pmem devices")
                    return
                else:
                    failures += 1
                    self.ssh.sendline("reboot_to_nova & exit")
                    self.ssh.expect(pexpect.EOF)
                    log.info("pmem devices missing, rebooting...")
                    time.sleep(logout_delay)
                    continue
            except pexpect.TIMEOUT as e:
                log.info("Reboot timed out")
                raise Exception("Reboot to nova failed")
            finally:
                try:
                    self.exit()
                except:
                    pass
                    
        raise Exception("Failed to reboot and create pmem devices after {} tries".format(failures))

            
class TimeoutException(Exception):
    pass

class ResetFailedException(Exception):
    pass

class LoggedProcess(object):
    def __init__(self, cmd, timeout=None):
        super(LoggedProcess, self).__init__()
        self.cmd = cmd
        self.task = None
        self.log = StringIO.StringIO()
        self.timeout = timeout
        if not self.cmd:
            self.cmd = [""]

    def go(self):
        self.start()
        while self.step():pass
        self.finished()

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
        if self.timeout is not None and time.clock() > self.start + self.timeout:
            raise TimeoutException()
        
        try:
            # read everything that remains
            while True:
                l = self.proc.stdout.read(1024)
                if not l:
                    break
                self.log.write(l)
                sys.stdout.write(l)

        except IOError as e:  # when there's nothing to read, we'll get an exception
            pass
        finally:
            if self.proc.poll() is not None: # if the process is dead, there's nothing more coming
                log.debug("return value: {}".format(self.proc.returncode))
                return False
            else:                            # otherwise, try again
                return True

        return True
    
    def finished(self):
        pass

    
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
                

class TestConfig(object):
    def __init__(self, 
                 name=None,
                 tests=None,
                 timeout=None,
                 test_class=None):
        self.name = name
        self.tests = tests
        self.test_class = test_class
        self.timeout = timeout


class XFSTests(LoggedProcess):
    def __init__(self, test_name, tconf, host):
        super(XFSTests, self).__init__(30*60)
        self.tconf = tconf
        self.test_name = test_name
        self.junit = None
        self.host = host
        self.dmesg = None
        self.cmd = "/usr/bin/ssh {} nova-testscripts/nova-ci/run.sh run-test xfstests {}".format(host.host, " ".join(self.tconf.tests)).split(" ")
    
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
        self.dmesg = Dmesg(self.host.host)
        LoggedProcess.start(self)
        self.dmesg.start()

    def step(self):
        
        try:
            return LoggedProcess.step(self) and self.dmesg.step()
        except TimeoutException as e:
            return False
        
    def finished(self):
        LoggedProcess.finished(self)
        self.dmesg.finished()
        self.dmesg.split_log()
        self.build_junit(self.dmesg.test_map)
        print self.junit

class NovaConfig(object):
    def __init__(self, 
                 name=None,
                 kernel_repo=None,
                 kernel_config_file=None,
                 module_args=None):
        self.name = name
        self.kernel_repo = kernel_repo
        self.kernel_config_file = kernel_config_file
        self.module_args = module_args

        

def main():
    log.basicConfig(level=log.DEBUG)

    parser = argparse.ArgumentParser()

    parser.add_argument("--host", required=True, help="Host to run on")
    parser.add_argument("--prompt", default=None, help="prompt to watch for")
    parser.add_argument("--tests", default=None, help="which tests to run")
    parser.add_argument("-v", default=False, action="store_true", help="be verbose")
    parser.add_argument("--no_rebuild_kernel", default=False, action="store_true", help="Don't rebuild or install the kernel")
    parser.add_argument("--dont_reset", default=False, action="store_true", help="Don't reset the host between runs")
    parser.add_argument("--dont_prep", default=False, action="store_true", help="Don't prepare the host before starting")
    args = parser.parse_args()

    if args.prompt is None:
        PROMPT = "swanson@".format(args.host)
    else:
        PROMPT = args.prompt
        
    host = Host(args.host, PROMPT, args=args)

    log.debug("Prompt = {}".format(PROMPT))
    global out
    
    if args.v:
        log.info("Being verbose")
        out=sys.stdout
    else:
        out = open("out", "w")
        
    nova_configs = [NovaConfig(name="baseline1",
                               kernel_repo=("git@github.com:NVSL/linux-nova.git", "HEAD"),
                               kernel_config_file="ubuntu.config",
                               module_args=""),
                    NovaConfig(name="baseline2",
                               kernel_repo=("git@github.com:NVSL/linux-nova.git", "HEAD"),
                               kernel_config_file="ubuntu.config",
                               module_args="wprotect=1")]

    tests = [TestConfig(name="xfstests1",
                        tests=["generic/092", "generic/080"],
                        timeout=100,
                        test_class=XFSTests),
             TestConfig(name="xfstests2",
                        tests=["generic/448", "generic/091"],
                        timeout=100,
                        test_class=XFSTests),
    ]

    if args.tests is None:
        args.tests = [x.name for x in tests]
    
    test_map = {x.name: x for x in tests}
    nconf_map = {x.name: x for x in nova_configs}
    print test_map

    for nconf in nova_configs:
        if not args.dont_prep:
            host.prepare_host_config(nconf) # update, build, and install the nova kernel
        try:
            for tconf in [test_map[i] for i in args.tests]:
                test_name = "{}/{}".format(nconf.name, tconf.name)

                try:
                    if not args.dont_reset:
                        host.reset_host(nconf)
                    host.prepare_pmem()
                    host.load_nova(nconf)
                except Exception as e:
                    log.error(e)
                    raise ResetFailedException()

                test = tconf.test_class(test_name, tconf, host)
                try:
                    test.go()
                except Exception as e:
                    log.error("{} failed: {}".format(test_name, e))
                finally:
                    with open("{}.junit".format(test_name.replace("/","_")), "w") as f:
                        f.write(test.junit)
                    
        except ResetFailedException as e:
            raise e
        
if __name__ == "__main__":
    main()
