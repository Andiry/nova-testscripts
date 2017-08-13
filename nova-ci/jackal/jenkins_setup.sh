set -v

wget -q -O - https://pkg.jenkins.io/debian/jenkins-ci.org.key | sudo apt-key add -
sudo sh -c 'echo deb http://pkg.jenkins.io/debian-stable binary/ > /etc/apt/sources.list.d/jenkins.list'
sudo apt-get -y update
sudo apt-get -y install jenkins
sudo apt-get install -y python-pip python-dev build-essential 
sudo pip install --upgrade pip 
sudo pip install --upgrade virtualenv 
sudo service jenkins start


sudo su jenkins ssh-keygen
echo Install this key at
echo

sudo cat ~jenkins/.ssh/id_rsa.pub
echo here
echo
echo 'https://console.cloud.google.com/compute/metadata/sshKeys?project=nvsl-nova-dev&organizationId=804593027890'


