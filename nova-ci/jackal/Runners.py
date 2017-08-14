import time
import pexpect
import logging as log
from JackalException import *
import json
import subprocess
import time
import sys

reboot_timeout=60 # seems to take about a minute, usually.
logout_delay=10

out = None

class Runner(object):
    def __init__(self,  prompt, args, log_out):
        self.prompt = prompt
        self.args = args
        self.log_out = log_out

    def create_prototype_instance(self, nconf):
        pass

    def shutdown(self):
        pass

    def delete(self):
        pass

    def do_expect(self, ssh, value, timeout=10):
        log.debug("Expecting {} (timeout={})".format(value, timeout))
        r = ssh.expect_exact(value, timeout=timeout)
        log.debug("Got it {})".format(value, timeout))
        return r
        
    def exit(self):
        self.ssh.sendline("exit")
        self.do_expect(self.ssh, pexpect.EOF, timeout=30)
        
    def open_shell(self, timeout=None, load_nova_ci=True):
        
        if timeout is None:
            timeout=reboot_timeout
        log.debug("Opening shell... (timeout={})".format(timeout))
        
        cmd = "/bin/bash ./ssh_retry.sh {}".format(self.get_hostname())
        self.ssh = pexpect.spawn(cmd,logfile=self.log_out)
        self.ssh.setwinsize(1000,1000)
        self.do_expect(self.ssh, self.prompt, timeout=timeout)
        if load_nova_ci:
            self.simple_command(". nova-testscripts/nova-ci/remote_funcs.sh")
            
    def simple_command(self, cmd, timeout=20):
        log.debug("simple_command {} timeout={}".format(cmd, timeout))
        self.ssh.sendline(cmd)
        self.do_expect(self.ssh, self.prompt, timeout=timeout)
        if not self.args.dont_double_expect:
            self.do_expect(self.ssh, self.prompt, timeout=timeout)
        
    def shell_cmd(self, cmd, timeout=20):
        log.info("shell_cmd begin: {} (timeout: {}s)".format(cmd, timeout))
        self.open_shell()
        self.simple_command(cmd, timeout=timeout)
        log.info("shell_cmd done : {}".format(cmd))
        self.exit()
        
    def update_nova_ci(self):
        log.info("update_nova_ci")
        self.open_shell(load_nova_ci=False)
        self.simple_command("[ -d nova-testscripts/ ] || git clone https://github.com/NVSL/nova-testscripts.git")
        self.simple_command("cd nova-testscripts; git pull")
        self.exit()

    def update_kernel(self, nconf):
        cmd = "update_kernel {} {} {}".format(nconf.kernel_config_file,
                                              nconf.kernel_repo[0],
                                              nconf.kernel_repo[1])

        self.shell_cmd(cmd, timeout=15*60)
        
    def build_kernel(self):
        self.shell_cmd("build_kernel", timeout=30*60)
        
    def install_kernel(self):
        self.shell_cmd("install_kernel", timeout=5*60)

    def get_old_host_config(self, nconf):
        return False
        r = self.gcloud("compute instances list")

    def schedule_reboot_to_nova(self):
        self.shell_cmd("schedule_reboot_to_nova")

    def default_to_nova(self):
        self.shell_cmd("default_to_nova")

    def delete_image(self, image_name):
        log.info("Deleting {}".format(image_name))
        self.gcloud("compute images delete {name}".format(name=image_name))
        
    def create_image(self, kernel_config):

        try:
            self.delete_image(self.image_name)
        except JackalException as e:
            log.info(e)
            
        r = self.gcloud("compute images create {name} --source-disk {src_name} --source-disk-zone {zone}"
                        .format(src_name=self.instance_name,
                                name=self.image_name,
                                zone=self.gce_zone))

        self.image_desc = r[0]
        
    def prepare_image(self, kernel_config, reboot=False, start_instance=True, reuse=False):
        log.info("prepare_image")
        self.instance_name = "{}{}".format(self.prefix, kernel_config.name)
        self.image_name = "{}-image".format(self.instance_name)
        
        if reuse:
            images = self.gcloud("compute images list")
            for im in images:
                if im["name"] == self.image_name:
                    self.image_desc = im
                    log.info("Reusing image {}".format(self.image_name))
                    return
        
        self.create_prototype_instance(kernel_config)
        self.update_nova_ci()
        if not self.args.dont_build_kernel:
            self.update_kernel(kernel_config)
            self.build_kernel()
            self.install_kernel()
        self.default_to_nova()
        self.shutdown()
        self.create_image(kernel_config)

    def load_nova(self, nconf):
        log.info("load_nova")
        self.shell_cmd("load_nova {}".format(nconf.module_args))
        self.shell_cmd("list_module_args nova")

    def mount_nova(self, nconf):
        self.shell_cmd("mount_nova".format(nconf.module_args))
        self.shell_cmd("df")
        
    def reset_host(self):
        self.gcloud("compute instances reset {}".format(self.instance_name))
        
    def reboot_to_nova(self, tries=0, force=False):
        log.info("Checking kernel version on {}".format(self.get_hostname()))
        self.open_shell()
        self.ssh.sendline("uname -a")
        try:
            t = self.do_expect(self.ssh, ["-nova",
                                          "-generic",
                                          pexpect.TIMEOUT])
            self.exit()
        except pexpect.TIMEOUT as e:
            t = 2
        
        if t == 0 and not force:
            log.info("Found nova kernel")
            return
        else:
            
            if t == 2:
                self.gcloud("compute instances reset {}".format(self.install_kernel))
            
            if tries == 2:
                log.info("Giving up.")
                raise CantRebootToNovaException("Couldn't reboot to nova")
            else:
                if force:
                    log.info("Forced reboot")
                else:
                    log.info("Found non-nova kernel")

                log.info("Rebooting...")
                self.shell_cmd("reboot_to_nova & exit")
                self.do_expect(self.ssh, pexpect.EOF)
                time.sleep(logout_delay)
                self.reboot_to_nova(first_try=False, tries=tries + 1) # won't reboot if we succeeded
                    
    def prepare_pmem(self, try_count=10):
        log.info("prepare_pmem Looking for pmem devices...")
        failures = 1
        restarts = 1
        while failures < try_count:
            log.info("Started waiting @ {}".format(time.time()))
            try:
                self.open_shell()
                self.ssh.sendline("check_pmem")
                r = self.do_expect(self.ssh, ["ok",
                                              "missing",
                                              pexpect.TIMEOUT,
                                              pexpect.EOF])
                self.exit()
            except pexpect.TIMEOUT:
                log.info("Timed out.")
                r = 2
            except pexpect.EOF:
                log.info("Unexpected EOF.")
                r = 2
            
            if r == 0:
                log.info("Found pmem devices")
                log.info("finished waiting @ {}".format(time.time()))
                return
            else:
                restarts += 1
                if r == 1:
                    log.info("pmem devices missing...")
                    failures += 1
                
                if (restarts % 5) == 0 and r != 1:
                    log.info("Recreating instance...")
                    self.delete()
                    self.create_instance_by_name(self.instance_name)
                else:
                    log.info("Rebooting...")
                    self.reset_host()
        log.info("finished waiting @ {}".format(time.time()))
        raise JackalException("Failed to reboot and create pmem devices after {} checks and {} restarts".format(try_count, restarts))

class VMRunner(Runner):
    def __init__(self, hostname, prompt, args, log_out):
        super(VMRunner, self).__init__(prompt, args, log_out)
        self.hostname = hostname
        
    def get_hostname(self):
        return self.hostname
    
class GCERunner(Runner):
    def __init__(self, prompt, args, log_out, prefix=None):
        super(GCERunner, self).__init__(prompt, args, log_out)
        
        self.args = args
        self.instance_desc = None
        self.instance_name = None

        self.image_desc = None
        self.image_name = None
        self.set_prefix(prefix)
            
        self.base_image = "nova-ci-image-v6"
        self.hosttype = "n1-highmem-8"
        self.gce_zone = "us-west1-c"

    def set_prefix(self, prefix):
        if prefix is None:
            self.prefix = ""
        else:
            self.prefix = prefix + "-"
        log.info("Setting prefix to {}".format(self.prefix))
    
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
        log.debug("stderr: " + err)
        log.debug("stdout: " + out)
        if proc.returncode != 0:
            log.info("Failed. returncode={}".format(proc.returncode))
            raise JackalException("'{}' failed (returncode={}): {} {}".format(cmd, proc.returncode, err, out)) 
        r = json.loads(out)
        log.info("Succcess!")
        return r

    def get_old_host_config(self, nconf):
        instance_name = "{}{}".format(self.prefix, nconf.name)
        log.info("get_old_host_config: {}".format(instance_name))
        r = self.gcloud("compute instances list")
        for host in r:
            if host["name"] == instance_name:
                log.info("get_old_host_config: found candidate...")
                if host["status"] != "RUNNING":
                    #self.gcloud("gcloud -q --format json compute instances 
                    self.instance_desc = [host]
                    self.instance_name = self.instance_desc[0]["name"]
                    self.hostname = self.instance_desc[0]["networkInterfaces"][0]["accessConfigs"][0]["natIP"]
                return True
        return False

    def prepare_instance(self, nova_config, reboot=False):
        log.info("prepare_instance start: {}".format(nova_config.name))
        #self.reboot_to_nova(force=reboot)
        self.prepare_pmem()
        self.load_nova(nova_config)
        self.mount_nova(nova_config)
        log.info("prepare_instance finished: {}".format(nova_config.name))

    
    def create_instance(self, nconf, reuse=False):
        name = "{}-{}".format(self.image_name, nconf.name)
        self.create_instance_by_name(name, reuse)
                 
    def create_instance_by_name(self, name, reuse=False):
        self.instance_name = name
        self.instance_desc = None
        
        if reuse:
            instances = self.gcloud("compute instances list")
            for i in instances:
                if i["name"] == self.instance_name:
                    self.instance_desc = i
                    log.info("Reusing instance {}".format(i["name"]))
                    break

        if self.instance_desc == None:
            try:
                self.cleanup_instance()
            except JackalException as e:
                log.error(e)

            self.instance_desc = self.gcloud("compute instances create {name} --image {image} --machine-type {m_type}". # --no-address
                                             format(name=self.instance_name,
                                                    image=self.image_name,
                                                    m_type=self.hosttype))[0]
            
            assert self.instance_name == self.instance_desc["name"], "Created instance has wrong name {} != {}".format(self.instance_desc, self.instance_desc[0]["name"])

        self.hostname = (self.instance_desc
                         ["networkInterfaces"]
                         [0]["accessConfigs"]
                         [0]["natIP"])

    def create_prototype_instance(self, kernel_config):
        self.instance_name = "{}{}".format(self.prefix, kernel_config.name)
        try:
            self.cleanup_by_name(self.instance_name)
        except JackalException as e:
            log.error(e)

        self.instance_desc = self.gcloud("compute instances create --image {image} --machine-type {m_type} {name}".
                                         format(name=self.instance_name,
                                                image=self.base_image,
                                                m_type=self.hosttype))
        
        assert self.instance_name == self.instance_desc[0]["name"], "Created instance has wrong name"
        self.hostname = (self.instance_desc
                         [0]["networkInterfaces"]
                         [0]["accessConfigs"]
                         [0]["natIP"])

        
    def shutdown(self):
        r = self.gcloud("compute instances stop {name}".format(name=self.instance_name))
        if r[0]["status"] == "TERMINATED":
            return
        raise JackalException("Couldn't terminate instance {}".format(self.instance_name))

    def delete_by_name(self, name):
        log.info("Deleting instance {}".format(name))
        for i in range(0,2):
            r = self.gcloud("compute instances delete {name}".format(name=name))
            if r == []:
                return
        raise JackalException("Couldn't terminate instance {}".format(name))
        
    def delete(self):
        self.delete_by_name(self.instance_name)


    def cleanup_by_name(self,name):
        log.info("cleaning up {}".format(name))
        r = self.gcloud("compute instances list")
        if name in [x["name"] for x in r]:
            log.info("Found one...deleting")
            try:
                self.delete_by_name(name)
            except JackalException as e:
                log.info("Couldn't cleanup {}: {}".format(name, e))
        else:
            log.info("Nothing to clean.")
        
    def cleanup_instance(self):
        self.cleanup_by_name(self.instance_name)
    
