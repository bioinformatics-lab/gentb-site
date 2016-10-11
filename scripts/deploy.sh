#!/bin/bash
#
# Simple bash script for updating a live instance.
#

cd "$(dirname "$0")"
cd ..

git pull
./manage migrate
./manage collectstatic

touch restart_me
