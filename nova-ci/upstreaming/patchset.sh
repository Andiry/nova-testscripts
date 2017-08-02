export VISUAL=emacs

function _mail() {
    # --cc=dan.j.williams@intel.com --to=linux-kernel@vger.kernel.org --to=linux-kernel@vger.kernel.org --to=linux-nvdimm@lists.01.org
    # --cc=andy.rudoff@intel.com --cc=coughlan@redhat.com

    stg mail  --auto --cc="Steven Swanson <steven.swanson@gmail.com>" -s 0 --all --kind RFC --smtp-server="`which esmtp` -t -i" --edit-cover -c ../upstreaming/cover.txt $*
}

function _patch() {
    label=$1
    shift
    stg new "$label" -m "NOVA: $*" --sign

    for file in $(cat); do
	(cd ../linux-nova; git diff v4.12 master $file) | patch -up1
	git add $file
    done
    stg refresh
    
}

function _delete() {
    stg delete $1
}

function _label() {
    echo $1
}

function _reset() {

    stg delete $(stg series --noprefix)
    
}

# Documentation

function _build_series() {
    _do_op _patch
    stg series -d
}

function _do_op () {
    op=$1
    $op doc "Documentation

A brief overview is in README.md.

Implementation and usage details are in Documentation/filesystems/nova.txt.

These two papers provide a detailed, high-level description of NOVA's design goals and approach:
   
   NOVA: A Log-structured File system for Hybrid Volatile/Non-volatile Main Memories (http://cseweb.ucsd.edu/~swanson/papers/FAST2016NOVA.pdf)

   Hardening the NOVA File System (http://cseweb.ucsd.edu/~swanson/papers/TechReport2017HardenedNOVA.pdf)


" <<EOF
Documentation/filesystems/00-INDEX
Documentation/filesystems/nova.txt
MAINTAINERS
README.md
EOF

    # Super block and layout
    $op super "Superblock and fs layout

FS Layout
======================

A Nova file systems resides in single PMEM device. Nova divides the device into
4KB blocks that are arrange like so:

 block
+-----------------------------------------------------+
|  0  | primary super block (struct nova_super_block) |
+-----------------------------------------------------+
|  1  | Reserved inodes                               |
+-----------------------------------------------------+
|  2  | reserved                                      |
+-----------------------------------------------------+
|  3  | Journal pointers                              |
+-----------------------------------------------------+
| 4-5 | Inode pointer tables                          |
+-----------------------------------------------------+
|  6  | reserved                                      |
+-----------------------------------------------------+
|  7  | reserved                                      |
+-----------------------------------------------------+
| ... | data pages                                    |
+-----------------------------------------------------+
| n-2 | replica reserved Inodes                       |
+-----------------------------------------------------+
| n-1 | replica super block                           |
+-----------------------------------------------------+


Superblock and Associated Structures
====================================

The beginning of the PMEM device hold the super block and its associated
tables.  These include reserved inodes, a table of pointers to the journals
Nova uses for complex operations, and pointers to inodes tables.  Nova
maintains replicas of the super block and reserved inodes in the last two
blocks of the PMEM area.

" <<EOF

fs/nova/super.c
fs/nova/super.h
fs/nova/nova.h
fs/nova/nova_def.h
EOF

    # PMEM allocation
    $op alloc "PMEM allocation system

Nova uses per-CPU allocators to manage free PMEM blocks.  On initialization,
NOVA divides the range of blocks in the PMEM device among the CPUs, and those
blocks are managed solely by that CPU.  We call these ranges of "allocation regions".

Some of the blocks in an allocation region have fixed roles.  Here's the
layout:

+-------------------------------+
| data checksum blocks          |
+-------------------------------+
| data parity blocks            |
+-------------------------------+
|                               |
| Allocatable blocks            |
|                               |
+-------------------------------+
| replica data parity blocks    |
+-------------------------------+
| replica data checksum blocks  |
+-------------------------------+

The first and last allocation regions, also contain the super block, inode
tables, etc. and their replicas, respectively.

Each allocator maintains a red-black tree of unallocated ranges (struct
nova_range_node).

Allocation Functions
--------------------

Nova allocate PMEM blocks using two mechanisms:

1.  Static allocation as defined in super.h

2.  Allocation for log and data pages via nova_new_log_blocks() and
nova_new_data_blocks().

Both of these functions allow the caller to control whether the allocator
preferes higher addresses for allocation or lower addresses.  We use this to
encourage meta data structures and their replicas to be far from one another.

PMEM Address Translation
------------------------

In Nova's persistent data structures, memory locations are given as offsets
from the beginning of the PMEM region.  nova_get_block() translates offsets to
PMEM addresses.  nova_get_addr_off() performs the reverse translation.

Cautious allocation
-------------------

The allocator allows the caller to provide some control over where the blocks
come from.  Nova uses this to allocate replicas of metadata far from one
another.

" <<EOF
fs/nova/balloc.c
fs/nova/balloc.h
EOF

    
    # Inode
    $op inode "Inode operations and structures

Nova maintains per-CPU inode tables, and inode numbers are striped across the
tables (i.e., inos 0, n, 2n,... on cpu 0; inos 1, n + 1, 2n + 1, ... on cpu 1).

The inodes themselves live in a set of linked lists (one per CPU) of 2MB
blocks.  The last 8 bytes of each block points to the next block.  Pointers to
heads of these list live in PMEM block INODE_TABLE0_START and are replicated in
PMEM block INODE_TABLE1_START.  Additional space for inodes is allocated on
demand.

To allocate inodes, Nova maintains a per-cpu "inuse_list" in DRAM holds a RB
tree that holds ranges of unallocated inode numbers.

" <<EOF 
fs/nova/inode.c 
fs/nova/inode.h
EOF

    # Inode logs
    $op logging "Log data structures and operations

Nova maintains a log for each inode that records updates to the inode's
metadata and holds pointers to the file data.  Nova makes updates to file data
and metadata atomic by atomically appending log entries to the log.

Each inode contains pointers to head and tail of the inode's log.  When the log
grows past the end of the last page, nova allocates additional space.  For
short logs (less than 1MB) , it doubles the length.  For longer logs, it adds a
fixed amount of additional space (1MB).

Log space is reclaimed during garbage collection.

Log Entries
-----------

There are eight kinds of log entry, documented in log.h.  The log entries have
several entries in common:

   1.  'epoch_id' gives the epoch during which the log entry was created.
   Creating a snapshot increiments the epoch_id for the file systems.

   2.  'trans_id' is filesystem-wide, monotone increasing, number assigned each
   log entry.  It provides an ordering over all FS operations.

   3.  'invalid' is true if the effects of this entry are dead and the log
   entry can be garbage collected.

   4.  'csum' is a CRC32 checksum for the entry.

Log structure
-------------

The logs comprise a linked list of PMEM blocks.  The tail of each block

contains some metadata about the block and pointers to the next block and
block's replica (struct nova_inode_page_tail).

+----------------+
| log entry      |
+----------------+
| log entry      |
+----------------+
| ...            |
+----------------+
| tail           |
|  metadata      |
|  -> next block |
+----------------+

" <<EOF
fs/nova/log.c
fs/nova/log.h
EOF

    # Journaling
    $op journal "Lite-weight journaling for complex ops

Nova uses a lightweight journaling mechanisms to provide atomicity for
operations that modify more than one on inode.  The journals providing logging
for two operations:

1.  Single word updates (JOURNAL_ENTRY)
2.  Copying inodes (JOURNAL_INODE)
                                                  
The journals are undo logs: Nova creates the journal entries for an operation,
and if the operation does not complete due to a system failure, the recovery
process rolls back the changes using the journal entries.

To commit, Nova drops the log.

Nova maintains one journal per CPU.  The head and tail pointers for each
journal live in a reserved page near the beginning of the file system.  

During recovery, Nova scans the journals and undoes the operations described by
each entry.

" <<EOF
fs/nova/journal.c
fs/nova/journal.h
EOF

    # File Operations
    $op file "File and directory operations

To access file data via read(), Nova maintains a radix tree in DRAM for each
inode (nova_inode_info_header.tree) that maps file offsets to write log
entries.  For directories, the same tree maps a hash of filenames to their
corresponding dentry.

In both cases, the nova populates the tree when the file or directory is opened
by scanning its log.

" <<EOF
fs/nova/dir.c
fs/nova/file.c
fs/nova/symlink.c
fs/nova/namei.c
EOF

    # Garbage Collection
    $op gc "Garbage collection

Nova recovers log space with a two-phase garbage collection system.  When a log
reaches the end of its allocated pages, Nova allocates more space.  Then, the
fast GC algorithm scans the log to remove pages that have no valid entries.
Then, it estimates how many pages the logs valid entries would fill.  If this
is less than half the number of pages in the log, the second GC phase copies
the valid entries to new pages.

For example:

+---+          +---+	        +---+
| I |	       | I |  	      	| V |
+---+	       +---+  Thorough	+---+
| V |	       | V |  	 GC   	| V |
+---+	       +---+   =====> 	+---+
| I |	       | I |  	      	| V |
+---+	       +---+	        +---+
| V |	       | V |  	        | V |
+---+	       +---+            +---+	
  |	         |	       
  V	         V             
+---+	       +---+ 	       
| I |	       | V | 	       
+---+	       +---+ 	       
| I | fast GC  | I | 	       
+---+  ====>   +---+ 	       
| I |	       | I | 	       
+---+	       +---+ 	       
| I |	       | V | 	       
+---+	       +---+ 	       
  |	       	
  V	       	
+---+	       	
| V |	       	
+---+	       	
| I |	       	
+---+	       	
| I |	       	
+---+	       	
| V |	       	
+---+            

" <<EOF
fs/nova/gc.c
EOF

    # mmap/dax
    $op dax "DAX code


NOVA leverages the kernel's DAX mechanisms for mmap and file data access.  Nova
maintains a red-black tree in DRAM (nova_inode_info_header.vma_tree) to track
which portions of a file have been mapped.

" <<EOF
fs/nova/dax.c
EOF

    # Data protection
    $op dprotect "File data protection


Nova protects data and metadat from corruption due to media errors and
"scribbles" -- software errors in the kernels that may overwrite Nova data.

Replication
-----------

Nova replicates all PMEM metadata structures (there are a few exceptions.  They
are WIP).  For structure, there is a primary and an "alternate" (denoted as
"alter" in the code).  To ensure that Nova can recover a consistent copy of the
data in case of a failure, Nova first updates the primary, and issues a persist
barrier to ensure that data is written to NVMM.  Then it does the same for the
alternate.

Detection
---------

Nova uses two techniques to detect data corruption.  For media errors, Nova
should always uses memcpy_from_pmem() to read data from PMEM, usually by
copying the PMEM data structure into DRAM.

To detect software-caused corruption, Nova uses CRC32 checksums.  All the PMEM
data structures in Nova include csum field for this purpose.  Nova also
computes CRC32 checksums each 512-byte slice of each data page.

The checksums are stored in dedicated pages in each CPU's allocation region.

                                                          replica
                                                 parity   parity 	
					         page	  page	  
            +---+---+---+---+---+---+---+---+    +---+    +---+       
data page 0 | 0 | 1 | 0 | 0 | 1 | 1 | 1 | 0 |    | 0 |    | 0 |  	
            +---+---+---+---+---+---+---+---+    +---+    +---+  	
data page 1 | 0 | 1 | 0 | 0 | 1 | 1 | 1 | 1 |    | 1 |    | 1 |  	
            +---+---+---+---+---+---+---+---+    +---+    +---+  	
data page 2 | 0 | 1 | 0 | 1 | 0 | 1 | 1 | 0 |    | 0 |    | 0 |  	
            +---+---+---+---+---+---+---+---+    +---+    +---+  	
data page 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |    | 0 |    | 0 |  	
            +---+---+---+---+---+---+---+---+    +---+    +---+  	
    ...                    ...                    ...      ...   

Recovery
--------

Nova uses replication to support recovery of metadata structures and
RAID4-style parity to recover corrupted data.

If Nova detects corruption of a metadata structure, it restores the structure
using the replica.

If it detects a corrupt slice of data page, it uses RAID4-style recovery to
restore it.  The CRC32 checksums for the page slices are replicated.

Cautious allocation
-------------------

To maximize its resilience to software scribbles, Nova allocate metadata
structures and their replicas far from one another.  It tries to allocate the
primary copy at a low address and the replica at a high address within the PMEM
region.

Write Protection
----------------

Finally, Nova supports can prevent unintended writes PMEM by mapping the entire
PMEM device as read-only and then disabling _all_ write protection by clearing
the WP bit the CR0 control register when Nova needs to perform a write.  The
wprotect mount-time option controls this behavior.

" <<EOF
fs/nova/checksum.c
fs/nova/parity.c
fs/nova/mprotect.c
fs/nova/mprotect.h
EOF
    
    # snapshots
    $op snapshots "Snapshot support

Nova supports snapshots to facilitate backups.

Taking a snapshot
-----------------

Each Nova file systems has a current epoch_id in the super block and each log
entry has the epoch_id attached to it at creation.  When the user creates a
snaphot, Nova increments the epoch_id for the file system and the old epoch_id
identifies the moment the snapshot was taken.

Nova records the epoch_id and a timestamp in a new log entry (struct
snapshot_info_log_entry) and appends it to the log of the reserved snapshot
inode (NOVA_SNAPSHOT_INODE) in the superblock.

Nova also maintains a radix tree (nova_sb_info.snapshot_info_tree) of struct
snapshot_info in DRAM indexed by epoch_id.

Nova also marks all mmap'd pages as read-only and uses COW to preserve file
contents after the snapshot.

Tracking Live Data
------------------

Supporting snapshots requires Nova to preserve file contents from previous
snapshots while also being able to recover the space a snapshot occupied after
its deletion.

Preserving file contents requires a small change to how Nova implements write
operations.  To perform a write, Nova appends a write log entry to the file's
log.  The log entry includes pointers to newly-allocated and populated NVMM
pages that hold the written data.  If the write overwrites existing data, Nova
locates the previous write log entry for that portion of the file, and performs
an \"epoch check\" that compares the old log entry's epoch_id to the file
system's current epoch_id.  If the comparison matches, the old write log entry
and the file data blocks it points to no longer belong to any snapshot, and
Nova reclaims the data blocks.

If the epoch_id's do not match, then the data in the old log entry belongs to
an earlier snapshot and Nova leaves the log entry in place.

Determining when to reclaim data belonging to deleted snapshots requires
additional bookkeeping.  For each snapshot, Nova maintains a \"snapshot log\"
that records the inodes and blocks that belong to that snapshot, but are not
part of the current file system image.

Nova populates the snapshot log during the epoch check: If the epoch_ids for
the new and old log entries do not match, it appends a log entry (either struct
snapshot_inode_entry or struct snapshot_file_write_entry) to the snapshot log
that the old log entry belongs to.  The log entry contains a pointer to the old
log entry, and the filesystem's current epoch_id as the delete_epoch_id.

To delete a snapshot, Nova removes the snapshot from the list of live snapshots
and appends its log to the following snapshot's log.  Then, a background thread
traverses the combined log and reclaims dead inode/data based on the delete
epoch_id: If the delete epoch_id for an entry in the log is less than or equal
to the snapshot's epoch_id, it means the log entry and/or the associated data
blocks are now dead.


Saving Snapshot State
---------------------

During a clean shutdown, Nova stores the snapshot information to PMEM.

Nova reserves an inode for storing snapshot information.  The log for the inode
contains an entry for each snapshot (struct snapshot_info_log_entry).  On
shutdown, Nova allocates one page (struct snapshot_nvmm_page) to store an array
of struct snapshot_nvmm_list.

Each of these lists (one per CPU) contains head and tail pointers to a linked
list of blocks (just like an inode log).  The lists contain a struct
snapshot_file_write_entry or struct snapshot_inode_entry for each operation
that modified file data or an inode.

Superblock
+--------------------+
|   ...              |
+--------------------+
| Reserved Inodes    |
+---+----------------+
|   |     ..         |
+---+----------------+
| 7 | Snapshot Inode |
|   | head           |
+---+----------------+
        /
       /
      / 
+---------+---------+---------+
|  Snap   |  Snap   |  Snap   |
| epoch=1 | epoch=4 | epoch=11|
|         |         |         |
|nvmm_page|nvmm_page|nvmm_page|
+---------+---------+---------+
     |
     |
+----------+   +--------+--------+
|  cpu 0   |   | snap 	| snap   |	
|   head   |-->| inode	| write	 |
|          |   | entry  | entry  |      
|          |   +--------+--------+
+----------+   +--------+--------+
|  cpu 1   |   | snap 	| snap   |
|   head   |-->| write	| write	 |
|          |   | entry  | entry  |
|          |   +--------+--------+
+----------+ 
|    ...   | 
+----------+   +--------+
|  cpu 128 |   | snap 	|
|   head   |-->| inode	|
|          |   | entry  |
|          |   +--------+
+----------+


" <<EOF
fs/nova/snapshot.c
fs/nova/snapshot.h
arch/x86/include/asm/io.h
arch/x86/mm/fault.c
arch/x86/mm/ioremap.c
include/linux/io.h
include/linux/mm.h
include/linux/mm_types.h
kernel/memremap.c
mm/memory.c
mm/mmap.c
mm/mprotect.c
drivers/nvdimm/pmem.c
EOF

    # Recovery
    $op recovery "Recovery code

Clean umount/mount
------------------

On a clean unmount, Nova saves the contents of many of its DRAM data structures
to PMEM to accelerate the next mount:

1. Nova stores the allocator state for each of the per-cpu allocators to the
   log of a reserved inode (NOVA_BLOCK_NODE_INO).
    
2. Nova stores the per-CPU lists of available inodes (the inuse_list) to the
   NOVA_BLOCK_INODELIST1_INO reserved inode.

3. Nova stores the snapshot state to PMEM as described above.

After a clean unmount, the following mount restores these data and then
invalidates them.

Recovery after failures
------------------------

In case of a unclean dismount (e.g., system crash), Nova must rebuild these
DRAM structures by scanning the inode logs.  Nova log scanning is fast because
per-CPU inode tables and per-inode logs allow for parallel recovery.

The number of live log entries in an inode log is roughly the number of extents
in the file.  As a result, Nova only needs to scan a small fraction of the NVMM
during recovery.

The Nova failure recovery consists of two steps:

First, Nova checks its lite weight journals and rolls back any uncommitted
transactions to restore the file system to a consistent state.

Second, Nova starts a recovery thread on each CPU and scans the inode tables in
parallel, performing log scanning for every valid inode in the inode table.
Nova use different recovery mechanisms for directory inodes and file inodes:
For a directory inode, Nova scans the log's linked list to enumerate the pages
it occupies, but it does not inspect the log's contents.  For a file inode,
Nova reads the write entries in the log to enumerate the data pages.

During the recovery scan Nova builds a bitmap of occupied pages, and rebuilds
the allocator based on the result. After this process completes, the file
system is ready to accept new requests.

During the same scan, it rebuilds the snapshot information and the list
available inodes.


" <<EOF
fs/nova/rebuild.c
fs/nova/bbuild.c
EOF
    
    # Sysfs and ioctl
    $op util "Sysfs and ioctl

Nova provides the normal ioctls for setting file attributes and provides a /proc-based interface for taking snapshots.
" <<EOF 
fs/nova/ioctl.c
fs/nova/sysfs.c
EOF


    # Stats and Performance Measurement
    $op perf "Performance measurement" <<EOF
fs/nova/perf.c
fs/nova/perf.h
fs/nova/stats.c
fs/nova/stats.h
EOF

    # Build infrastructure
    $op build "Build infrastructure" <<EOF
fs/Kconfig
fs/Makefile
fs/nova/Kconfig
fs/nova/Makefile
EOF
}
