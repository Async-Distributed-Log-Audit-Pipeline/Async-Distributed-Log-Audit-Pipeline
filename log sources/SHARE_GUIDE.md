# Project Sharing & Running Guide

This guide ensures that anyone can run the Student Management System project with minimal effort. The project is fully containerized using Docker.

## Prerequisites
- **Docker Desktop** installed and running on your machine.
- No Java, Maven, or IDE installations are required to run the project.

## How to Run the Project

1. **Clone or Download** the project folder.
2. **Open a Terminal** (PowerShell, Command Prompt, or Bash) in the project root directory.
3. **Execute the following command:**
   ```bash
   docker compose up --build
   ```
4. **Wait for all services to start.** The first run may take a few minutes as it downloads images and builds containers.

## Service Access URLs

Once the containers are running, you can access the following:

| Component | URL |
| :--- | :--- |
| **Frontend UI** | [http://localhost:8081](http://localhost:8081) |
| **Service Registry (Eureka)** | [http://localhost:8761](http://localhost:8761) |
| **API Gateway** | [http://localhost:9191](http://localhost:9191) |

## Troubleshooting

- **Port Conflicts:** Ensure ports 8081, 8761, 9191, and the database ports (3307-3310) are not being used by other applications.
- **Docker Resources:** Ensure Docker has at least 4GB of RAM allocated.
- **Wait for DB:** If a service fails to connect to the database on the first try, it will retry automatically. Wait a few moments for the databases to fully initialize.

## For the Evaluator
This project demonstrates a **Microservices Architecture** using Spring Boot, React, and MySQL. It features:
- Centralized API Gateway
- Service Discovery with Eureka
- AOP-based Audit Logging
- Containerized deployment for full portability across Operating Systems.
