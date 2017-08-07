#!/usr/bin/env python
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
import json
import pwd


reboot_timeout=180 # seems to take about a minute, usually.
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

class Runner(object):
    def __init__(self,  prompt, args):
        self.prompt = prompt
        self.args = args

    def create(self, name):
        pass

    def shutdown(self):
        pass

    def delete(self):
        pass

    def exit(self):
        self.ssh.sendline("exit")
        self.ssh.expect(pexpect.EOF)
        
    def test(self, conf):
        self.open_shell()
        self.simple_command("echo hello")
        self.exit()
        self.update_nova_ci()
        #self.update_kernel(conf)
        
    def open_shell(self, timeout=None, load_nova_ci=True):
        if timeout is None:
            timeout=reboot_timeout
            
        cmd = "/bin/bash ./ssh_retry.sh {}".format(self.get_hostname())
        self.ssh = pexpect.spawn(cmd, logfile=out)
        self.ssh.expect(self.prompt, timeout=timeout)
        if load_nova_ci:
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
        log.info("update_nova_ci")
        self.open_shell(load_nova_ci=False)
        self.simple_command("cd nova-testscripts/; git pull")
        self.exit()

    def update_kernel(self, nconf):
        cmd = "update_kernel {} {} {}".format(nconf.kernel_config_file,
                                                       nconf.kernel_repo[0],
                                                       nconf.kernel_repo[1])
        self.shell_cmd(cmd, timeout=10*60)
        
    def build_kernel(self):
        self.shell_cmd("build_kernel", timeout=30*60)
        
    def install_kernel(self):
        self.shell_cmd("install_kernel", timeout=5*60)

    def get_old_host_config(self, name):
        return False
        r = self.gcloud("compute instances list")
        
    def prepare_host_config(self, nconf, reboot=False, start_instance=True, reuse=False):
        log.info("prepare_host_config")
#        if start_instance:
        if not (reuse and self.get_old_host_config(nconf.name)):
            self.create(nconf.name)
#        elif reboot:
#            self.reboot_to_nova()
            
        self.update_nova_ci()
        if not self.args.no_update_kernel:
            self.update_kernel(nconf)
        if not self.args.no_rebuild_kernel:
            self.build_kernel()
        if not self.args.no_install_kernel:
            self.install_kernel()
        #self.reboot_to_nova(force=True)

    def hard_reboot(self):
        log.info("hard_reboot")
        raise NotImplemented()

    def load_nova(self, nconf):
        log.info("load_nova")
        self.shell_cmd("load_nova {}".format(nconf.module_args))
        self.shell_cmd("list_module_args nova")

    def mount_nova(self, nconf):
        log.info("mount_nova")
        self.shell_cmd("mount_nova".format(nconf.module_args))
        self.shell_cmd("df")
        
    def reset_host(self, nconf):
        if not self.soft_reboot():
            self.hard_reboot()
        self.reboot_to_nova()
        
    def soft_reboot(self):
        log.info("soft_reboot")
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
        
    def reboot_to_nova(self, first_try=True, force=False):
        log.info("Checking kernel version on {}".format(self.get_hostname()))
        self.open_shell()
        self.ssh.sendline("uname -a")
        t = self.ssh.expect(["-nova",
                             "-generic"])
        if t == 0 and not force:
            log.info("Found nova kernel")
            return
        else:
            if not first_try:
                log.info("Giving up.")
                raise CantRebootToNovaException("Couldn't reboot to nova")
            else:
                if force:
                    log.info("Forced reboot")
                else:
                    log.info("Found non-nova kernel")

                log.info("Rebooting...")
                self.ssh.sendline("reboot_to_nova & exit")
                self.ssh.expect(pexpect.EOF)
                time.sleep(logout_delay)
                self.reboot_to_nova(first_try=False) # won't reboot if we succeeded
                    
    def prepare_pmem(self):
        log.info("prepare_pmem Looking for pmem devices...")
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

class VMRunner(Runner):
    def __init__(self, hostname, prompt, args):
        super(VMRunner, self).__init__(prompt, args)
        self.hostname = hostname

    def get_hostname(self):
        return self.hostname
    
class GCERunner(Runner):
    def __init__(self, prompt, args):
        super(GCERunner, self).__init__(prompt, args)
        
        self.args = args
        self.instance_desc = None
        self.instance_name = None

        self.image = "nova-ci-image-v5"
        self.hosttype = "n1-highmem-8"
        self.gce_zone = "us-west1-c"
        
    def get_hostname(self):
        return self.hostname

    def gcloud(self, cmd):
        full_cmd = ("gcloud -q --format=json".
                    format(self.gce_zone).split(" ") +
                    cmd.split(" "))
        log.info(full_cmd)
        proc = subprocess.Popen(full_cmd,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = proc.communicate()
        log.debug(err)
        log.debug(out)
        if proc.returncode != 0:
            raise Exception("'{}' failed (returncode={}): {}".format(cmd,proc.returncode)) 
        r = json.loads(out)
        return r

    def get_old_host_config(self, name):
        log.info("get_old_host_config: {}".format(name))
        r = self.gcloud("compute instances list")
        for host in r:
            if host["name"] == name:
                log.info("get_old_host_config: found candidate...")
                if host["status"] != "RUNNING":
                    #self.gcloud("gcloud -q --format json compute instances 
                    self.instance_desc = [host]
                    self.instance_name = self.instance_desc[0]["name"]
                    self.hostname = self.instance_desc[0]["networkInterfaces"][0]["accessConfigs"][0]["natIP"]

                return True
        return False
        
    def create(self, name):
        try:
            self.cleanup(name)
        except:
            pass
        self.instance_desc = self.gcloud("compute instances create --image {image} --machine-type {m_type} {name}".format(name=name, image=self.image, m_type=self.hosttype))
        self.instance_name = self.instance_desc[0]["name"]
        self.hostname = self.instance_desc[0]["networkInterfaces"][0]["accessConfigs"][0]["natIP"]

    def shutdown(self):
        for i in range(0,2):
            r = self.gcloud("compute instances stop {name}".format(name=self.instance_name))
            if r[0]["status"] == "TERMINATED":
                return
        raise Exception("Couldn't terminate instance {}".format(self.instance_name))

    def delete_by_name(self, name):
        log.info("Deleting instance {}".format(name))
        for i in range(0,2):
            r = self.gcloud("compute instances delete {name}".format(name=name))
            if r == []:
                return
        raise Exception("Couldn't terminate instance {}".format(name))
        
    def delete(self):
        self.delete_by_name(self.instance_name)

        
    def cleanup(self, name):
        """ Cleanup after old runners... """
        log.info("cleaning up {}".format(name))
        r = self.gcloud("compute instances list")
        if name in [x["name"] for x in r]:
            log.info("Found one...deleting".format(name))
            try:
                self.delete_by_name(name)
            except Exception as e:
                log.info("Couldn't cleanup {}: {}".format(name, e))
        else:
            log.info("Nothing to clean.".format(name))
                    
        
            
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
        self.dmesg = Dmesg(self.runner.get_hostname())
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

    parser.add_argument("--prompt", default=None, help="prompt to watch for")
    parser.add_argument("--tests", default=[], nargs="*", help="which tests to run")
    parser.add_argument("--configs", default=[], nargs="*", help="which configurations to run")
    parser.add_argument("-v", default=False, action="store_true", help="be verbose")
    parser.add_argument("--runner", default="fixed", help="Run tests on GCE")
    parser.add_argument("--host", help="Runner to run on (for 'fixed')")
    
    parser.add_argument("--reuse_instances", default=False, action="store_true", help="If an existing instance exists, use it")
    parser.add_argument("--no_rebuild_kernel", default=False, action="store_true", help="Don't rebuild the kernel")
    parser.add_argument("--no_update_kernel", default=False, action="store_true", help="Don't update the kernel")
    parser.add_argument("--no_install_kernel", default=False, action="store_true", help="Don't install the kernel")
    parser.add_argument("--dont_reset", default=False, action="store_true", help="Don't reset the host between runs")
    parser.add_argument("--dont_prep", default=False, action="store_true", help="Don't prepare the host before starting")
    parser.add_argument("--dont_kill_runner", default=False, action="store_true", help="Don't kill the runner when finished")
    args = parser.parse_args()

    if args.prompt is None:
        PROMPT = "{}@".format(pwd.getpwuid(os.getuid()).pw_name, args.host)
    else:
        PROMPT = args.prompt
        

    log.debug("Prompt = {}".format(PROMPT))
    global out

    try:
        os.mkdir("results")
    except:
        pass
    out = open("results/run_test.log", "w")
    if args.v:
        log.info("Being verbose")
        out=Tee([sys.stdout, out])
        
    nova_configs = [NovaConfig(name="baseline1",
                               kernel_repo=("https://github.com/NVSL/linux-nova.git", "HEAD"),
                               kernel_config_file="gce.v4.12.config",
                               module_args=""),
                    NovaConfig(name="baseline2",
                               
                               kernel_repo=("https://github.com/NVSL/linux-nova.git", "HEAD"),
                               kernel_config_file="gce.v4.12.config",
                               module_args="wprotect=1")]

    tests = [TestConfig(name="xfstests1",
                        tests=["generic/092", "generic/080"],
                        timeout=100,
                        test_class=XFSTests),
             TestConfig(name="xfstests2",
                        tests=["generic/448", "generic/091"],
                        timeout=100,
                        test_class=XFSTests),
             TestConfig(name="xfstests-all",
                        tests=[], # this means all of them.
                        timeout=40*60,
                        test_class=XFSTests),
    ]

    if args.runner == "fixed":
        runner = VMRunner(args.host, PROMPT, args=args)
    elif args.runner == "gce":
        runner = GCERunner(PROMPT, args=args)
    else:
        raise Exception("Illegal runner: {}".format(args.runner))

    if args.tests == []:
        args.tests = [x.name for x in tests]
    
    if args.configs == []:
        args.configs = [x.name for x in nova_configs]
    
    test_map = {x.name: x for x in tests}
    nconf_map = {x.name: x for x in nova_configs}

    log.info("Configs : " + " ".join(args.configs))
    log.info("tests : " + " ".join(args.tests))

    nconfs_to_run = [nconf_map[i] for i in args.configs]
    tests_to_run = [test_map[i] for i in args.tests]
    
    for nconf in nconfs_to_run:
        try:
            runner.prepare_host_config(nconf, reuse=args.reuse_instances) # update, build, and install the nova kernel

            for tconf in tests_to_run:
                test_name = "{}/{}".format(nconf.name, tconf.name)
                log.info("Running {}".format(test_name))

                try:
                    if not args.dont_reset:
                        runner.reset_host(nconf)
                    runner.prepare_pmem()
                    runner.load_nova(nconf)
                    runner.mount_nova(nconf)
                except Exception as e:
                    log.error(e)
                    raise ResetFailedException()

                test = tconf.test_class(test_name, tconf, runner)
                try:
                    test.go()
                except Exception as e:
                    log.error("{} failed: {}".format(test_name, e))
                finally:
                    with open("results/{}.junit".format(test_name.replace("/","_")), "w") as f:
                        f.write(test.junit)
                    
        except ResetFailedException as e:
            print e
            raise e
        except Exception as e:
            print e
            raise e
        finally:
            log.info("Cleaning up {}...".format(nconf.name))
            if not args.dont_kill_runner:
                runner.shutdown()
            if not args.dont_kill_runner:
                runner.delete()
        
if __name__ == "__main__":
    main()
