#!/usr/bin/env bash
# Zips a directory relative to its parent (i.e. missing out intermediate directories)

src=$1
base_dir=$2
name_file=$3
method=$4
case $method in
1)
cp $1 $2/$3
;;
2)
rsync -av $1/* $2/$3 --exclude='filtered_func_data.ica'
;;
esac
