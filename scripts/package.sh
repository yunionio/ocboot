#!/bin/bash

p='ocboot'
d=`date +"%Y-%m-%d"`
b=$(git rev-parse --abbrev-ref HEAD)
v=`git log --branches="${b}*" -n 1 |pcregrep -io '(?<=commit )\w{8}'`
a="$p"-"$d"-"${b/\//-}"-"$v".tar.gz
git archive $b --prefix="$p/" | gzip > $a
echo "Archived:"
echo `readlink -f $a`

