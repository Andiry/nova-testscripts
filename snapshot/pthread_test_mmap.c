#define _GNU_SOURCE

#include<stdio.h>
#include<fcntl.h>
#include<time.h>
#include<string.h>
#include<malloc.h>
#include<stdlib.h>
#include<stdint.h>
#include<stdbool.h>
#include<pthread.h>
#include<sys/mman.h>
#include<unistd.h>
#include<sys/time.h>



#define END_SIZE	(4UL * 1024 * 1024) 

volatile int finish;

struct pthread_data {
	int pid;
	char *data;
	unsigned long long length;
	volatile long long count;
};

void *pthread_transfer(void *arg)
{
	struct pthread_data *pdata = arg;
	char *data = pdata->data;
	unsigned long long length = pdata->length;
	long k;
	unsigned long long count = length / 8;
	unsigned long long i;

	while(1) {
		for (i = 0; i < count; i++) {
			k = *(long *)(data + i * 8);
			k++;
			*(long *)(data + i * 8) = k;
			if (i > 0 && ((i & 65535) == 0))
				pdata->count += 65536;
		}
		pdata->count += 65536;
		if (finish)
			break;
	}

	pthread_exit(0);
	return NULL;
}

int main(int argc, char **argv)
{
	pthread_t *pthreads;
	struct pthread_data *pids;
	int i;
	int sec = 0;
	size_t len;
	unsigned long long count, new_count;
	char file_size_num[20];
	unsigned long long FILE_SIZE;
	char *buf;
	int num_threads;
	int fd;
	int seconds;
	char *data;
	char unit;
	size_t ret;

	if (argc < 4) {
		printf("Usage: ./pthread_test_mmap $num_threads $FILE_SIZE $seconds\n");
		return 0;
	}

	num_threads = atoi(argv[1]);
	if (num_threads <= 0 || num_threads > 16) {
		printf("num threads %d? limit to 1\n", num_threads);
		num_threads = 1;
	}

	seconds = atoi(argv[3]);
	if (seconds <= 5)
		seconds = 5;

	strcpy(file_size_num, argv[2]);
	len = strlen(file_size_num);
	unit = file_size_num[len - 1];
	file_size_num[len - 1] = '\0';
	FILE_SIZE = atoll(file_size_num);
	switch (unit) {
	case 'K':
	case 'k':
		FILE_SIZE *= 1024;
		break;
	case 'M':
	case 'm':
		FILE_SIZE *= 1048576;
		break;
	case 'G':
	case 'g':
		FILE_SIZE *= 1073741824;
		break;
	default:
		printf("ERROR: FILE_SIZE should be #K/M/G format.\n");
		return 0;
		break;
	}

	if (FILE_SIZE < END_SIZE)
		FILE_SIZE = END_SIZE;

	printf("# pthreads: %d, file size %llu, running for %d seconds\n",
			num_threads, FILE_SIZE, seconds);

	if (posix_memalign((void *)&buf, END_SIZE, END_SIZE)) // up to 64MB
		return 0;

	fd = open("/mnt/ramdisk/test1", O_CREAT | O_RDWR, 0640);

	count = FILE_SIZE / END_SIZE;
	for (i = 0; i < count; i++) {
		ret = write(fd, buf, END_SIZE);
		if (ret != END_SIZE)
			printf("ERROR: size incorrect: required %lu, "
				"returned %lu\n", END_SIZE, ret);
	}

	data = (char *)mmap(NULL, FILE_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_POPULATE, fd, 0);

	//Allocate the threads
	pthreads = (pthread_t *)malloc(num_threads * sizeof(pthread_t));
	pids = (struct pthread_data *)malloc(num_threads * sizeof(struct pthread_data));
	for (i = 0; i < num_threads; i++) {
		pids[i].pid = i;
		pids[i].length = FILE_SIZE / num_threads;
		pids[i].data = data + i * pids[i].length;
		pids[i].count = 0;
		pthread_create(pthreads + i, NULL, pthread_transfer, (void *)(pids + i)); 
	}

	count = 0;
	while (1) {
		sleep(1);
		sec++;
		new_count = 0;
		for (i = 0; i < num_threads; i++)
			new_count += pids[i].count;
		printf("Second %d, count %llu\n", sec, new_count - count);
		count = new_count;
		if (sec >= seconds)
			break;
	}

	printf("Finish.\n");
	finish = 1;
	close(fd);
	for (i = 0; i < num_threads; i++) {
		pthread_join(pthreads[i], NULL);
	}
	free(buf);
	free(pthreads);
	free(pids);
	munmap(data, FILE_SIZE);
	return 0;
}
