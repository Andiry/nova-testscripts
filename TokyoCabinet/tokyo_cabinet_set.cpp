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

#define ITERATIONS 1
#define NUM_KEYS 100000
#define KEY_SIZE 8
#define VALUE_SIZE 1024

struct option_t {
    unsigned int iterations = ITERATIONS;
    unsigned int num_keys   = NUM_KEYS;
    unsigned int key_size   = KEY_SIZE;
    unsigned int value_size = VALUE_SIZE;
};

void parse_cmd(struct option_t *o, char *s) {
    std::string iterations("--iterations=");
    std::string num_keys("--num-keys=");
    std::string key_size("--key-size=");
    std::string value_size("--value-size=");

    std::string arg(s);
    if (!arg.compare(0, iterations.size(), iterations))
        o->iterations = std::stoi(arg.substr(iterations.size()));
    else if (!arg.compare(0, num_keys.size(), num_keys))
        o->num_keys = std::stoi(arg.substr(num_keys.size()));
    else if (!arg.compare(0, key_size.size(), key_size))
        o->key_size = std::stoi(arg.substr(key_size.size()));
    else if (!arg.compare(0, value_size.size(), value_size))
        o->value_size = std::stoi(arg.substr(value_size.size()));
    else {
        std::cerr << "invalid argument: " << s << std::endl;
        exit(-1);
    }
}

option_t parse_options(int argc, char *argv[]) {
    // TODO: really parse arguments to form options
    option_t option;
    for (unsigned int i = 1; i < argc; i++)
        parse_cmd(&option, argv[i]);

#if 1
    std::cout << "iterations: " << option.iterations << std::endl;
    std::cout << "num keys:   " << option.num_keys << std::endl;
    std::cout << "key size:   " << option.key_size << std::endl;
    std::cout << "value size: " << option.value_size << std::endl;
    std::cout << std::endl;
#endif
    return option;
}


TCHDB *tokyocabinet_setup() {
    TCHDB *hdb = tchdbnew();
    if (!tchdbopen(hdb, "dump.tch", HDBOWRITER | HDBOCREAT)) {
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

    std::cout << "tokyocabinet-set: " << ((double)timer.duration()/1e9) << " s" << std::endl;
}

int main(int argc, char *argv[])
{
    option_t o = parse_options(argc, argv);

    TCHDB *hdb = tokyocabinet_setup();

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
