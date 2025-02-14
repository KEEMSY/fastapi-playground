import os
import time
from typing import Dict, Any

import docker  # 라이브러리를 설치하여, requirements.txt에 업데이트 필요

from tests.config import get_test_settings


def is_container_ready(container):
    container.reload()
    return container.status == "running"


def wait_for_stable_status(container, stable_duration=3, interval=1):
    start_time = time.time()
    stable_count = 0
    while time.time() - start_time < stable_duration:
        if is_container_ready(container):
            stable_count += 1
        else:
            stable_count = 0

        if stable_count >= stable_duration / interval:
            return True

        time.sleep(interval)
    return False


def create_docker_network(network_name: str = "test-network") -> None:
    client = docker.from_env()
    try:
        network = client.networks.get(network_name)
        print(f"Network '{network_name}' already exists.")
    except docker.errors.NotFound:
        network = client.networks.create(network_name)
        print(f"Created network '{network_name}'")


def remove_existing_container(client: docker.DockerClient, container_name: str) -> None:
    try:
        container = client.containers.get(container_name)
        print(f"Container '{container_name}' exists. Stopping and removing...")
        container.stop()
        container.remove()
        print(f"Container '{container_name}' stopped and removed")
    except docker.errors.NotFound:
        print(f"Container '{container_name}' does not exist.")


def wait_for_postgres(container, timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            result = container.exec_run("pg_isready")
            if result.exit_code == 0:
                result = container.exec_run(
                    f'psql -U root -d test-project -c "SELECT 1"'
                )
                if result.exit_code == 0:
                    print("PostgreSQL is fully ready!")
                    return True
            print(f"Waiting for PostgreSQL... (exit code: {result.exit_code})")
        except Exception as e:
            print(f"Error checking PostgreSQL status: {e}")
        time.sleep(2)
    return False


def start_database_container() -> Any:
    settings = get_test_settings()
    client = docker.from_env()

    # 기존 컨테이너 확인 및 제거
    try:
        existing_container = client.containers.get("test-db")
        print(f"Removing existing container: {existing_container.id}")
        existing_container.remove(force=True)
    except docker.errors.NotFound:
        print("No existing container found")

    container_config = {
        "image": "postgres:latest",
        "name": "test-db",
        "detach": True,
        "environment": {
            "POSTGRES_USER": settings.POSTGRES_USER,
            "POSTGRES_PASSWORD": settings.POSTGRES_PASSWORD,
            "POSTGRES_DB": settings.POSTGRES_DB,
        },
        "ports": {"5432/tcp": settings.POSTGRES_PORT},
        "healthcheck": {
            "test": ["CMD-SHELL", "pg_isready -U root -d test-project"],
            "interval": 1000000000,
            "timeout": 1000000000,
            "retries": 5,
            "start_period": 1000000000,
        },
    }

    try:
        container = client.containers.run(**container_config)
        print(f"Started new container: {container.id}")

        if not wait_for_postgres(container):
            container.stop()
            raise Exception("Database failed to start")

        return container

    except Exception as e:
        print(f"Error starting container: {e}")
        raise
