#!/bin/perl

$file1 = $ARGV[0];
$file2 = $ARGV[1];

open $FILE, $file1 or die "Cannot open $file1 read :$!";
while ($line=<$FILE>) {
    if ($line =~ /\[OVERALL\], Throughput\(ops\/sec\), (.*)/) {
        print $1;
        print "\t";
    }
}

open $INFILE, $file2 or die "Cannot open $file2 read :$!";

while ($line=<$INFILE>) {
    if ($line =~ /\[OVERALL\], Throughput\(ops\/sec\), (.*)/) {
        print $1;
        print "\t";
    }

    if ($line =~ /\[READ\], AverageLatency\(us\), (.*)/) {
        print $1;
        print "\t";
    }

    if ($line =~ /\[READ\], 99thPercentileLatency\(us\), (.*)/) {
        print $1;
        print "\t";
    }

    if ($line =~ /\[UPDATE\], AverageLatency\(us\), (.*)/) {
        print $1;
        print "\t";
    }

    if ($line =~ /\[UPDATE\], 99thPercentileLatency\(us\), (.*)/) {
        print $1;
        print "\n";
    }

}
