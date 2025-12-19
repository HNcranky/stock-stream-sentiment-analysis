#!/bin/bash

echo "=============================================="
echo "🧹 STARTING MAINTENANCE CLEANUP"
echo "=============================================="

# 1. Clean Local Docker
echo "1. Cleaning Host Docker..."
docker system prune -f --volumes
docker image prune -a -f

# 2. Clean Minikube Docker
echo "2. Cleaning Minikube Docker Environment..."
eval $(minikube docker-env)
docker system prune -f --volumes
docker image prune -a -f

# 3. Check Disk Usage
echo "=============================================="
echo "💾 DISK USAGE CHECK (Minikube)"
minikube ssh -- df -h | grep /var/lib/docker

echo "=============================================="
echo "✅ CLEANUP COMPLETE! System should be healthy."
echo "=============================================="
