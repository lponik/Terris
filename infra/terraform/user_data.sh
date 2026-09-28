#!/bin/bash
set -euxo pipefail

dnf install -y docker

systemctl enable docker
systemctl start docker

usermod -aG docker ec2-user

mkdir -p /opt/terris
chown ec2-user:ec2-user /opt/terris