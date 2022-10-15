#!/bin/bash

set -eu

# Symlink sv directories and start runit
rm -rf /etc/service/hypercorn
rm -rf /etc/service/nginx

ln -s /etc/sv/hypercorn /etc/service/hypercorn
ln -s /etc/sv/nginx /etc/service/nginx

# Create logfiles
mkdir -p /var/log/hypercorn
mkdir -p /var/log/nginx
touch /var/log/hypercorn/current
touch /var/log/nginx/current

# Launch runit daemon and tail logs to keep in foreground
runsvdir /etc/service & /usr/src/bin/tail-logs.sh