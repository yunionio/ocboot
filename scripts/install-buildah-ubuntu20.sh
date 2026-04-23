#!/bin/bash

# https://gist.github.com/sebastianwebber/2c1e9c7df97e05479f22a0d13c00aeca
#
# prereq packages
sudo apt-get update

sudo apt-get install -y wget ca-certificates gnupg2

# add repo and signing key
VERSION_ID=$(lsb_release -r | cut -f2)

echo "deb http://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_${VERSION_ID}/ /" | sudo tee /etc/apt/sources.list.d/devel-kubic-libcontainers-stable.list

curl -Ls https://download.opensuse.org/repositories/devel:kubic:libcontainers:stable/xUbuntu_$VERSION_ID/Release.key | sudo apt-key add -

sudo apt-get update

# install buildah and podman
sudo apt install buildah -y

# fix known issue 11745 with [machine] entry
sudo sed -i 's/^\[machine\]$/#\[machine\]/' /usr/share/containers/containers.conf
