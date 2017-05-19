#include <iostream>
#include <tcutil.h>
#include <tchdb.h>
#include <string>
#include <cstring>
#include <sstream>
#include <iomanip>
#include <vector>
#include <sys/wait.h>

#include "timer.h"

#define ITERATIONS 3
#define NUM_KEYS 1000000
#define KEY_SIZE 8
#define VALUE_SIZE 1024
#define PMEM_MODE 1
#define FALLOC 1

struct option_t {
    unsigned int iterations;
    unsigned int num_keys;
    unsigned int key_size;
    unsigned int value_size;
    unsigned int pmem_mode;
    unsigned int falloc;
};

void parse_cmd(struct option_t *o, char *s) {
    std::string iterations("--iterations=");
    std::string num_keys("--num_keys=");
    std::string key_size("--key_size=");
    std::string value_size("--value_size=");
    std::string pmem_mode("--pmem_mode=");
    std::string falloc("--fallocate=");

    std::string arg(s);
    if (!arg.compare(0, iterations.size(), iterations))
        o->iterations = std::stoi(arg.substr(iterations.size()));
    else if (!arg.compare(0, num_keys.size(), num_keys))
        o->num_keys = std::stoi(arg.substr(num_keys.size()));
    else if (!arg.compare(0, key_size.size(), key_size))
        o->key_size = std::stoi(arg.substr(key_size.size()));
    else if (!arg.compare(0, value_size.size(), value_size))
        o->value_size = std::stoi(arg.substr(value_size.size()));
    else if (!arg.compare(0, pmem_mode.size(), pmem_mode))
        o->pmem_mode = std::stoi(arg.substr(pmem_mode.size()));
    else if (!arg.compare(0, falloc.size(), falloc))
        o->falloc = std::stoi(arg.substr(falloc.size()));
    else {
        std::cerr << "invalid argument: " << s << std::endl;
        exit(-1);
    }
}

static void parse_options(option_t &o, int argc, char *argv[]) {
    o.iterations = ITERATIONS;
    o.num_keys   = NUM_KEYS;
    o.key_size   = KEY_SIZE;
    o.value_size = VALUE_SIZE;
    o.pmem_mode = PMEM_MODE;
    o.falloc = FALLOC;

    // TODO: really parse arguments to form options
    std::cout << argc << std::endl;
    for (unsigned int i = 1; i < argc; i++)
        parse_cmd(&o, argv[i]);

    std::cout << "iterations: " << o.iterations << std::endl;
    std::cout << "num keys:   " << o.num_keys << std::endl;
    std::cout << "key size:   " << o.key_size << std::endl;
    std::cout << "value size: " << o.value_size << std::endl;
    std::cout << "pmem mode:  " << o.pmem_mode << std::endl;
    std::cout << "fallocate:  " << o.falloc << std::endl;
    std::cout << std::endl;

    return;
}


TCHDB *tokyocabinet_setup(option_t &o) {
    int flag = HDBOWRITER | HDBOCREAT;

    if (o.pmem_mode == 1)
	flag |= HDBOMOVNT;
    else if (o.pmem_mode == 2)
	flag |= HDBOFLUSH;

    if (o.falloc)
	flag |= HDBOFALLOC;

    TCHDB *hdb = tchdbnew();
    if (!tchdbopen(hdb, "/mnt/ramdisk/dump.tch", flag)) {
        int ecode = tchdbecode(hdb);
        std::cerr << "open error: " << tchdberrmsg(ecode) << std::endl;
        tchdbdel(hdb);
        exit(-1);
    }
    return hdb;
}

void tokyocabinet_cleanup(TCHDB *hdb) {
    if (!tchdbclose(hdb)) {
        std::cout << "clean up finished!" << std::endl;
        int ecode = tchdbecode(hdb);
        std::cerr << "close error: " << tchdberrmsg(ecode) << std::endl;
        tchdbdel(hdb);
        exit(-1);
    }
    tchdbdel(hdb);
}

void tokyocabinet_bench(TCHDB *hdb, option_t *o) {
    // create cmd string
    std::string value = std::string(o->value_size, 'a');
    double second;

    ggc::Timer timer("tokyocabinet-set");
    timer.start();

    for (long long counter = 0; counter < o->num_keys; counter++) {
        // modify the key a little bit
        std::stringstream cs;
        cs << std::setfill('0') << std::setw(o->key_size) << counter;
        std::string key = cs.str();
        // call tokyocabinet set API 
        if (!tchdbput2(hdb, key.c_str(), value.c_str())) {
            int ecode = tchdbecode(hdb);
            std::cerr << "dbput error: " << tchdberrmsg(ecode) << std::endl;
            tokyocabinet_cleanup(hdb);
        }
	tchdbsync(hdb);
    }
    std::cout << "SET: " << o->num_keys << " completed!" << std::endl;

    timer.stop();

    // FIXME: Should I delete all records?
    // TokyoCabinet is probably using append-only file
    // deleting all keys does not make a difference

    second = (double)timer.duration() / 1e9;
    std::cout << "tokyocabinet-set: " << second << " s, "
		<< o->num_keys / second << " ops/s" << std::endl;
}

int main(int argc, char *argv[])
{
    option_t o;
    parse_options(o, argc, argv);

    TCHDB *hdb = tokyocabinet_setup(o);
    system("echo 1 > /proc/fs/NOVA/pmem0/timing_stats");

    for (unsigned int i = 0; i < o.iterations; i++) {
        if (i) std::cout << std::endl;
        tokyocabinet_bench(hdb, &o);
#if 1
	// clean up /mnt/ramdisk
	std::vector<char*> args;
	args.push_back((char*)"/bin/rm");
	args.push_back((char*)"-rf");
	args.push_back((char*)"/mnt/ramdisk/*.aof");
	args.push_back((char*)"/mnt/ramdisk/dump.*");
	args.push_back(0);

	pid_t pid = fork();
	switch (pid) {
	case -1: std::cerr << "Error forking!" << std::endl; exit(-1);
	case 0: // child
		execv(args[0], &args.front());
		exit(0);
	default: // parent
		int status;
		waitpid(pid, &status, 0);
	}
#endif
    }

    tokyocabinet_cleanup(hdb);
    return 0;
}
