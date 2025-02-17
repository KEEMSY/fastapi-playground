from pydantic import BaseModel


class TestSettings(BaseModel):
    """테스트 환경 설정"""

    # Database settings
    POSTGRES_USER: str = "root"
    POSTGRES_PASSWORD: str = "test"
    POSTGRES_DB: str = "test-project"
    POSTGRES_PORT: int = 5432
    POSTGRES_HOST: str = "localhost"
    POSTGRES_IMAGE: str = "postgres:latest" # 필요에 따라 버전 명시

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "test"
    REDIS_DB: int = 0
    REDIS_IMAGE: str = "redis:7.0-alpine"
    REDIS_CONTAINER_NAME: str = "test-redis"

    # Docker settings
    DOCKER_NETWORK_NAME: str = "fastapi-test-project_default"
    DOCKER_CONTAINER_NAME: str = "test-db"

    # Healthcheck settings
    HEALTHCHECK_INTERVAL: int = 1000000000
    HEALTHCHECK_TIMEOUT: int = 1000000000
    HEALTHCHECK_RETRIES: int = 5
    HEALTHCHECK_START_PERIOD: int = 1000000000

    @property
    def DATABASE_URL(self) -> str:
        """데이터베이스 URL 생성"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def REDIS_URL(self) -> str:
        """Redis URL 생성"""
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


def get_test_settings() -> TestSettings:
    """테스트 설정 인스턴스 반환"""
    return TestSettings()
