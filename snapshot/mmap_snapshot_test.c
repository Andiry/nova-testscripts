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


#define END_SIZE	(64UL * 1024 * 1024) 

int main(int argc, char **argv)
{
	int i;
	size_t len;
	unsigned long long count;
	char file_size_num[20];
	unsigned long long FILE_SIZE;
	unsigned long buf_size;
	char *buf;
	int fd;
	char *data;
	char unit;
	size_t ret;

	if (argc < 2) {
		printf("Usage: ./mmap_snapshot_test $FILE_SIZE\n");
		return 0;
	}

	strcpy(file_size_num, argv[1]);
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

	buf_size = END_SIZE;
	if (buf_size > FILE_SIZE)
		buf_size = FILE_SIZE;

	if (posix_memalign((void *)&buf, buf_size, buf_size)) // up to 64MB
		return 0;

	fd = open("/mnt/ramdisk/test1", O_CREAT | O_RDWR, 0640);

	count = FILE_SIZE / buf_size;
	for (i = 0; i < count; i++) {
		ret = write(fd, buf, buf_size);
		if (ret != buf_size)
			printf("ERROR: size incorrect: required %lu, "
				"returned %lu\n", buf_size, ret);
	}

	data = (char *)mmap(NULL, FILE_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_POPULATE, fd, 0);

	printf("Mmap finish, sleep for 10 seconds\n");

	fflush(stdout);
	for (i = 0; i < 10; i++) {
		sleep(1);
		printf(".");
		fflush(stdout);
	}

	printf("\nSleep finish.\n");

	*(data) = 'c';

	free(buf);
	munmap(data, FILE_SIZE);
	close(fd);

	return 0;
}
