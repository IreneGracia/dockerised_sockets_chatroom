# Docker Chat (Server + Client)

A simple TCP chat application with a Dockerised server and Dockerised clients.

## Overview

The server listens on a configurable address and port and writes chat activity to a backup file, while each client connects to the server using a username; Docker Compose is used to build images, run the server, and start one or more interactive client containers on the same Docker network.

## Expected project structure

Docker Compose expects the following layout:

```
.
├── docker-compose.yml
├── server/
│   ├── server.py
│   └── Dockerfile
└── client/
    ├── client.py
    └── Dockerfile
```

## Build the Docker images

From the repository root:

```bash
docker compose build
```

## Run the server

Start the server container:

```bash
docker compose up server
```

The server listens on port `8000` and writes its backup file to `/data/Backup.txt` inside the container.

## Run a client

Start an interactive client container (replace the username as needed):

```bash
docker compose run --rm client python client.py Pedro
```

You can run multiple clients by opening additional terminals and using different usernames.

## Persisted data

The server mounts a Docker volume at `/data`, so the backup file is preserved across container restarts.

## Environment variables

### Server
- `ADDRESS` – bind address
- `PORT` – listening port (default: 8000)
- `BACKUP_PATH` – path to backup file

### Client
- `ADDRESS` – server hostname (set to `server` in Docker Compose)
- `PORT` – server port
