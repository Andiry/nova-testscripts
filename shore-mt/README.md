# Shore-MT

Shore-MT is a database implemenation.
git repo:
https://bitbucket.org/shoremt/shore-kits/src


Usage:
~~~
# touch /mnt/ramdisk/db-tpcc-200
# mkdir /mnt/ramdisk/log-tpcc-200
# ./shore_kits -c tpcc-200 -s baseline -d normal -r
~~~

Run:
~~~
measure 100 1 20 60 0 2 0	// Mix
measure 100 1 20 60 1 2 0	// New order
measure 100 1 20 60 2 2 0	// Payment
~~~

Note:
Shore-MT uses write_iter to access files. Disable it for DP and WP.
