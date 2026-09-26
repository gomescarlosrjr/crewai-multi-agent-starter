#!/bin/bash
# Script para subir o Redis usando Docker Compose

echo "🔴 Iniciando Redis..."
echo ""

# Verifica se o Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker não está rodando. Por favor, inicie o Docker primeiro."
    exit 1
fi

# Para o Redis se já estiver rodando
echo "🛑 Parando Redis existente (se houver)..."
docker-compose down redis

# Sobe o Redis
echo "🚀 Subindo Redis..."
docker-compose up -d redis

# Verifica se o Redis subiu corretamente
sleep 2
if docker ps | grep -q redis; then
    echo ""
    echo "✅ Redis está rodando!"
    echo "📍 Porta: 6379"
    echo "🔗 Host: localhost"
    echo ""
    echo "Para parar o Redis, execute:"
    echo "  docker-compose down redis"
    echo ""
    echo "Para ver os logs do Redis:"
    echo "  docker-compose logs -f redis"
else
    echo ""
    echo "❌ Erro ao subir o Redis. Verifique os logs:"
    echo "  docker-compose logs redis"
    exit 1
fi
