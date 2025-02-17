import os
import time
from typing import Dict, Any

import docker 
import aioredis

from tests.config import get_test_settings, TestSettings


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


def get_container_config(settings: TestSettings) -> Dict[str, Any]:
    """컨테이너 설정을 반환하는 함수"""
    return {
        "image": settings.POSTGRES_IMAGE, 
        "name": settings.DOCKER_CONTAINER_NAME,
        "detach": True,
        "environment": {
            "POSTGRES_USER": settings.POSTGRES_USER,
            "POSTGRES_PASSWORD": settings.POSTGRES_PASSWORD,
            "POSTGRES_DB": settings.POSTGRES_DB,
        },
        "ports": {"5432/tcp": settings.POSTGRES_PORT},
        "healthcheck": {
            "test": ["CMD-SHELL", f"pg_isready -U {settings.POSTGRES_USER} -d {settings.POSTGRES_DB}"],
            "interval": settings.HEALTHCHECK_INTERVAL,  
            "timeout": settings.HEALTHCHECK_TIMEOUT,    
            "retries": settings.HEALTHCHECK_RETRIES,    
            "start_period": settings.HEALTHCHECK_START_PERIOD, 
        },
        "network": settings.DOCKER_NETWORK_NAME
    }


def ensure_network_exists(network_name: str):
    """Docker 네트워크가 없으면 생성"""
    client = docker.from_env()
    try:
        client.networks.get(network_name)
    except docker.errors.NotFound:
        client.networks.create(network_name)


def start_database_container() -> Any:
    settings = get_test_settings()
    ensure_network_exists(settings.DOCKER_NETWORK_NAME)  # 네트워크 확인/생성
    client = docker.from_env()

    try:
        existing_container = client.containers.get(settings.DOCKER_CONTAINER_NAME)
        print(f"Removing existing container: {existing_container.id}")
        existing_container.remove(force=True)
    except docker.errors.NotFound:
        print("No existing container found")

    try:
        container = client.containers.run(**get_container_config(settings))
        print(f"Started new container: {container.id}")

        if not wait_for_postgres(container):
            container.stop()
            raise Exception(f"Database failed to start: {settings.DOCKER_CONTAINER_NAME}")

        return container

    except Exception as e:
        print(f"Error starting container {settings.DOCKER_CONTAINER_NAME}: {e}")
        raise


def start_redis_container():
    """Redis 컨테이너 시작"""
    settings = get_test_settings()
    client = docker.from_env()

    # 기존 컨테이너 제거
    try:
        container = client.containers.get(settings.REDIS_CONTAINER_NAME)
        container.remove(force=True)
        print(f"Removed existing Redis container: {container.id}")
    except docker.errors.NotFound:
        print("No existing Redis container found")

    # Redis 컨테이너 설정
    container_config = {
        "image": settings.REDIS_IMAGE,
        "name": settings.REDIS_CONTAINER_NAME,
        "ports": {f"6379/tcp": settings.REDIS_PORT},
        "environment": {"REDIS_PASSWORD": settings.REDIS_PASSWORD},
        "command": f"redis-server --requirepass {settings.REDIS_PASSWORD}",
        "detach": True,
        "network": settings.DOCKER_NETWORK_NAME
    }

    try:
        container = client.containers.run(**container_config)
        print(f"Started new Redis container: {container.id}")

        # Redis 준비 대기
        for i in range(30):
            try:
                redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                redis.ping()
                redis.close()
                print("Redis is ready!")
                break
            except Exception as e:
                if i == 29:  # 마지막 시도
                    raise Exception(f"Redis failed to start: {e}")
                time.sleep(1)
                print(f"Waiting for Redis... (attempt {i+1}/30)")

        return container

    except Exception as e:
        print(f"Error starting Redis container: {e}")
        raise
