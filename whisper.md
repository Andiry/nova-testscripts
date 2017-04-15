# Manuals
Read the following files before running the benchmakrs:
* [WHISPER readme](https://github.com/NVSL/whisper-NOVA/blob/master/README.md) for general instructions on running benchmarks.
* [NVSL notes](https://github.com/NVSL/whisper-NOVA/blob/master/Notes.md) on building and running benchmarks.
* Notes on Mnemosyne and its benchmakrs can be found [here](https://github.com/NVSL/whisper-NOVA/blob/master/Mnemosyne.md).
* Notes on N-Store and Echo can be found [here](https://github.com/NVSL/whisper-NOVA/blob/master/N-Store.md).

# Test script
The test script ([script.py](https://github.com/NVSL/whisper-NOVA/blob/master/script.py)) 
should be used with the following options:

## Build benchmarks
```bash
./script.py -b -w {ycsb, tpcc, echo, redis, ctree, hashmap, memcached, vacation}
```

## Running benchmarks
```bash
./script.py -r -z large -w {ycsb, tpcc, echo, redis, ctree, hashmap, memcached, vacation}
```

## Running benchmarks + periodic checkpointing
```bash
./script.py -r -z large -n -w {ycsb, tpcc, echo, redis, ctree, hashmap, memcached, vacation}
```
