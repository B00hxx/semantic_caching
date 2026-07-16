#!/bin/bash

docker rm my-redis && docker rm ollama
docker run -d --gpus=all -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
docker run --name my-redis -p 6379:6379 -d redis