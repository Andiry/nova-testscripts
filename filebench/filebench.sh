#!/bin/sh

echo "Do you want to install Bison? [Y/n] "
read answer
if [ "$answer" == "Y" ] || [ "$answer" == "y" ]; then
	sudo apt-get install bison
fi

echo "Do you want to install Flex? [Y/n] "
read answer
if [ "$answer" == "Y" ] || [ "$answer" == "y" ]; then
	sudo apt-get install flex
fi

echo "------------------------------------------------------------------------------
				              Downloading FileBench
------------------------------------------------------------------------------
"

git clone https://github.com/filebench/filebench.git

cd filebench

libtoolize
aclocal
autoheader
automake --add-missing
autoconf

./configure
make
sudo make install
