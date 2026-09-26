#!/bin/bash
# Script to start Redis using Docker Compose

echo "🔴 Starting Redis..."
echo ""

# Check whether Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Stop Redis if it's already running
echo "🛑 Stopping existing Redis (if any)..."
docker-compose down redis

# Start Redis
echo "🚀 Bringing Redis up..."
docker-compose up -d redis

# Check whether Redis came up correctly
sleep 2
if docker ps | grep -q redis; then
    echo ""
    echo "✅ Redis is running!"
    echo "📍 Port: 6379"
    echo "🔗 Host: localhost"
    echo ""
    echo "To stop Redis, run:"
    echo "  docker-compose down redis"
    echo ""
    echo "To view Redis logs:"
    echo "  docker-compose logs -f redis"
else
    echo ""
    echo "❌ Failed to start Redis. Check the logs:"
    echo "  docker-compose logs redis"
    exit 1
fi
