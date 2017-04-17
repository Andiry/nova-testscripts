# make-snapshots.py
When running application, taking snapshots at one second interval.

Usage:
~~~
# python make-snapshots.py #FS #num
~~~

# pthread_test_mmap
Multi-thread random write mmap application

Usage:
~~~
# ./pthread_test_mmap $num_threads $FILE_SIZE $seconds
~~~

# mmap_snapshot_test
Simple application that does mmap() and sleeps.

Usage:
~~~
# ./mmap_snapshot_test $FILE_SIZE
~~~
