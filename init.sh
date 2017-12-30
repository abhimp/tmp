#!/bin/bash

sudo apt-get install -y python-netifaces bpython python-netaddr

pwd > /tmp/config.log

python /local/configurePath.py >> /tmp/config.log
