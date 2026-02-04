# TCP Chat Application (Client–Server)

This project is a simple multi-client chat application built using Python’s low-level TCP sockets, designed to demonstrate core networking, concurrency and systems fundamentals.

## Architecture & Design Decisions

The system follows a classic client–server model over TCP. The server listens for incoming connections and spawns a dedicated thread per client to handle message reception and broadcasting, ensuring clients operate independently without blocking each other. Thread safety is maintained using `Lock` objects around shared state (connected clients and conversation logs), which prevents race conditions when clients join, leave or send messages concurrently.

Graceful shutdown is handled using OS signal handling (`SIGINT`, `SIGTERM`) and `Event` objects, allowing both the server and clients to terminate cleanly without leaving hanging sockets. The application can run in both local and Dockerised environments.

A background daemon thread periodically persists chat history to disk.

The application is containerised using Docker and docker-compose to ensure consistent runtime behaviour across environments.

## Limitations and possible future improvements

- Replace per-client threads with asyncio .
- Add authentication or unique username enforcement.
- Introduce structured logging.

## Running the Project

```bash
docker-compose up --build
python client.py <username>
```
