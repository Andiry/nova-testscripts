#!/usr/bin/env python2

import os
import re
import sys
import time
import shlex
import random
import subprocess32 as sproc

# the .f files must exist in the current directory
workloads = ['fileserver', 'varmail', 'webproxy', 'webserver', 'mongo']
# the number of times each workload repeats
worktimes = [          3 ,        5 ,         3 ,          1 ,      5 ]
# the max number of concurrent co-workers for each workload
coworkers = [          1 ,        2 ,         2 ,          1 ,      2 ]

# for non-replica cases
# worktimes = [          4 ,        5 ,         3 ,          1 ,      5 ]
# coworkers = [          1 ,        2 ,         2 ,          1 ,      2 ]

# r for raw string notation
wkfiledir = r'./workfile'
novamount = r'/mnt/ramdisk'

# execute a shell command, blocking
def shell(cmdstr):
    cmds = shlex.split(cmdstr)
    sproc.check_output(cmds)

# create a process, non blocking
def process(cmdstr):
    cmds = shlex.split(cmdstr)
    proc = sproc.Popen(cmds, stdout=sproc.PIPE, stderr=sproc.PIPE)
    return proc

# working directory in the nova file system
def workerdir(wkload, wktime, wker):
    return novamount + '/' + wkload + '-' + str(wktime) + '-' + str(wker)

# filebench workfile name
def benchfile(wkload, wktime, wker):
    return wkfiledir + '/' + wkload + '-' + str(wktime) + '-' + str(wker) + '.f'

# create a filebench workfile
def create_workfile(wkload, wktime, wker):
    ifile = wkload + '.f'
    ofile = benchfile(wkload, wktime, wker)
    wkdir = workerdir(wkload, wktime, wker)
    with open(ifile, 'r') as source, open(ofile, 'w') as target:
        for line in source:
            line = re.sub(r'^set.*\$dir=.*', r'set $dir=' + wkdir, line)
            target.write(line)
    return ofile

# create a worker process
def create_workproc(wkid, wktime, wker):
    if wktime < 0 or wktime > worktimes[wkid]:
        print 'worktime error', wktime
        return None

    wkload = workloads[wkid]
    wkfile = create_workfile(wkload, wktime, wker)
    if not os.path.isfile(wkfile):
        print 'workfile error', wkfile
        return None
    wkcmd = 'filebench -f ' + wkfile
    wkproc = process(wkcmd), wkid, wktime, wker

    return wkproc

# gap line to separate finished jobs
def gapline(wkload, wktime, wker):
    title = wkload + '-' + str(wktime) + '-' + str(wker)
    return '\n' + '-' * 10 + title + '-' * 10 + '\n'

# randomly pick some files to delete
def randrm(topdir):
    if novamount not in topdir:
        print 'Error:',
        print topdir, 'does not contain', novamount
        return
    if not os.path.isdir(topdir):
        print 'Error:',
        print topdir, 'is not a valid directory'
        return
    delcnt = 0
    for root, dirs, files in os.walk(topdir, topdown=False):
        for name in files:
            dice = random.randint(0, 2) # 0, 1, 2
            if dice == 0:
                delcnt += 1
                os.remove(os.path.join(root, name))
    print 'deleted', delcnt, 'files from', topdir

# repeat one workload some times
def repeat_one_workload(wkload, times):
    if wkload not in workloads:
        print 'Error: unknown workload', wkload
        return

    for _ in xrange( int(times) ):
        wktime = time.clock()
        wkfile = create_workfile(wkload, wktime, 'x')
        if not os.path.isfile(wkfile):
            print 'workfile error', wkfile
            return
        wkcmd = 'filebench -f ' + wkfile
        shell(wkcmd)
# --- #

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'This program should not work if /dev/pmem0 is less than 64 GB.'
        print 'To run it for sure, type appropriate arguments.'
        print '   run all worloads:  ./stress.py all'
        print '   run mongo 5 times: ./stress.py mongo 5'
        sys.exit(0)
    elif sys.argv[1] != 'all':
        if len(sys.argv) < 3:
            print 'Error: missing arguments!'
        else:
            repeat_one_workload(sys.argv[1], sys.argv[2])
        sys.exit(0)

    shell('mkdir -p ' + wkfiledir)
    logfile = open(wkfiledir + '/results.log', 'w')
    logfile.write('stress testing nova file system')

    workprocs = []
    for workid, workload in enumerate(workloads):
        for worker in xrange(coworkers[workid]):
            if worktimes[workid] == 0: continue
            worktime = worktimes[workid]
            workproc = create_workproc(workid, worktime, worker)
            if workproc != None:
                workprocs.append(workproc)
                print '{0:12s} {1} created for worker {2}'.format(
                      workload, worktime, worker)
                worktimes[workid] -= 1
            else:
                print 'Error: create worker process failed!'
                sys.exit(1)

    print '\nwaiting for worker processes to finish'
    print 'run ./swatch.sh to monitor the run status'
    print 'kill a process if it takes unexpected long time'
    print 'if workloads are too much for the pmem space, try to reduce the'
    print 'number of coworkers, worktimes, or nfiles, runtime in the workfile'

    while any(workproc is not None for workproc in workprocs):
        for idx, workproc in enumerate(workprocs):
            if workproc is None: continue
            proc, workid, worktime, worker = workproc
            workload = workloads[workid]
            rc = proc.poll()
            if rc != None:
                output, error = proc.communicate()

                print gapline(workload, worktime, worker)
                print output
                logfile.write( gapline(workload, worktime, worker) )
                logfile.write(output)

                if rc != 0:
                    print 'Error:',
                    print '{0:12s} {1} by worker {2}'.format(
                          workload, worktime, worker), 'returns non-zero code!'
                    workprocs[idx] = None
                    continue
                else:
                    print '{0:12s} {1} by worker {2} finished'.format(
                          workload, worktime, worker)

                if worktimes[workid] > 0:
                    print '{0:12s} {1} by worker {2}'.format(
                          workload, worktime, worker),
                    randrm( workerdir(workload, worktime, worker) )

                    worktime = worktimes[workid]
                    workproc = create_workproc(workid, worktime, worker)
                    if workproc != None:
                        workprocs[idx] = workproc
                        print '{0:12s} {1} created for worker {2}'.format(
                              workload, worktime, worker)
                        worktimes[workid] -= 1
                    else:
                        print 'Error: create worker process failed!'
                        sys.exit(1)
                else: # no more workload to do
                    workprocs[idx] = None
        time.sleep(0.1)

    logfile.close()
