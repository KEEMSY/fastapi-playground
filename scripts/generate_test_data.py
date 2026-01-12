#!/usr/bin/env python3
"""
성능 테스트용 대용량 데이터 생성 스크립트

Usage:
    # 동기 방식으로 10만 건 생성 (기본값)
    python scripts/generate_test_data.py

    # 비동기 방식으로 10만 건 생성
    python scripts/generate_test_data.py --async

    # 커스텀 설정
    python scripts/generate_test_data.py --records=50000 --batch=10000

    # Docker 환경에서 실행
    docker exec -it playground python scripts/generate_test_data.py
"""

import argparse
import asyncio
import os
import random
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

# 카테고리 및 상태 옵션
CATEGORIES = [
    "technology", "science", "business", "sports", "entertainment",
    "politics", "health", "education", "lifestyle", "travel"
]
STATUSES = ["active", "inactive", "pending", "archived"]

# 제목 템플릿
TITLE_TEMPLATES = [
    "Understanding {topic} in Modern World",
    "A Complete Guide to {topic}",
    "How {topic} is Changing Everything",
    "The Future of {topic}",
    "Why {topic} Matters Now",
    "Best Practices for {topic}",
    "Getting Started with {topic}",
    "Advanced {topic} Techniques",
    "Common Mistakes in {topic}",
    "Expert Tips for {topic}",
]

# 토픽 목록
TOPICS = [
    "AI", "Cloud Computing", "Data Science", "Machine Learning",
    "Web Development", "DevOps", "Cybersecurity", "Blockchain",
    "IoT", "5G Networks", "Kubernetes", "Microservices",
    "Python", "FastAPI", "PostgreSQL", "Redis",
    "Docker", "CI/CD", "Agile", "TDD"
]

# 컨텐츠 템플릿
CONTENT_TEMPLATES = [
    "This comprehensive article explores {topic} and its applications in modern software development. ",
    "Learn about the latest trends in {topic} and how they can benefit your projects. ",
    "A deep dive into {topic} covering fundamental concepts and advanced implementations. ",
    "Practical guide to implementing {topic} in production environments. ",
    "Explore best practices and common pitfalls when working with {topic}. ",
]


def generate_content(topic: str) -> str:
    """랜덤 컨텐츠 생성"""
    templates = random.sample(CONTENT_TEMPLATES, k=random.randint(2, 5))
    content = "".join([t.format(topic=topic) for t in templates])
    # 컨텐츠를 여러 번 반복하여 적당한 크기로 만듦
    return content * random.randint(3, 10)


def generate_record(index: int) -> Dict:
    """단일 레코드 생성"""
    topic = random.choice(TOPICS)
    template = random.choice(TITLE_TEMPLATES)

    return {
        "title": f"{template.format(topic=topic)} #{index}",
        "content": generate_content(topic),
        "category": random.choice(CATEGORIES),
        "status": random.choice(STATUSES),
        "view_count": random.randint(0, 100000),
        "created_at": datetime.utcnow() - timedelta(
            days=random.randint(0, 365),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        ),
        "updated_at": datetime.utcnow() - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23)
        ),
    }


def generate_batch(start_index: int, batch_size: int) -> List[Dict]:
    """배치 데이터 생성"""
    return [generate_record(i) for i in range(start_index, start_index + batch_size)]


def sync_bulk_insert(db_url: str, total_records: int = 100000, batch_size: int = 5000):
    """동기 방식 Bulk Insert"""
    print(f"\n{'='*60}")
    print(f"동기 방식 데이터 생성 시작")
    print(f"{'='*60}")
    print(f"총 레코드 수: {total_records:,}")
    print(f"배치 크기: {batch_size:,}")
    print(f"데이터베이스: {db_url.split('@')[1] if '@' in db_url else db_url}")
    print(f"{'='*60}\n")

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)

    # 테이블 존재 확인 및 생성
    with engine.connect() as conn:
        # performance_test_data 테이블이 없으면 생성
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS performance_test_data (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                category VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                view_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()

        # 인덱스 생성
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_perf_test_title ON performance_test_data(title);
            CREATE INDEX IF NOT EXISTS ix_perf_test_category ON performance_test_data(category);
            CREATE INDEX IF NOT EXISTS ix_perf_category_status ON performance_test_data(category, status);
            CREATE INDEX IF NOT EXISTS ix_perf_created_at_status ON performance_test_data(created_at, status);
        """))
        conn.commit()

    start_time = time.time()
    inserted_count = 0

    with Session() as session:
        try:
            for batch_start in range(0, total_records, batch_size):
                batch_end = min(batch_start + batch_size, total_records)
                batch_data = generate_batch(batch_start, batch_end - batch_start)

                # Bulk insert using execute
                session.execute(
                    text("""
                        INSERT INTO performance_test_data
                        (title, content, category, status, view_count, created_at, updated_at)
                        VALUES (:title, :content, :category, :status, :view_count, :created_at, :updated_at)
                    """),
                    batch_data
                )
                session.commit()

                inserted_count += len(batch_data)
                progress = inserted_count / total_records * 100
                elapsed = time.time() - start_time
                rate = inserted_count / elapsed if elapsed > 0 else 0

                print(f"진행률: {progress:6.2f}% | "
                      f"삽입: {inserted_count:>8,}/{total_records:,} | "
                      f"속도: {rate:,.0f} rec/s | "
                      f"경과: {elapsed:.1f}s")

        except Exception as e:
            session.rollback()
            print(f"\n오류 발생: {e}")
            raise

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"완료!")
    print(f"{'='*60}")
    print(f"총 레코드: {inserted_count:,}")
    print(f"소요 시간: {elapsed:.2f}초")
    print(f"평균 속도: {inserted_count / elapsed:,.0f} records/sec")
    print(f"{'='*60}\n")


async def async_bulk_insert(db_url: str, total_records: int = 100000, batch_size: int = 5000):
    """비동기 방식 Bulk Insert"""
    print(f"\n{'='*60}")
    print(f"비동기 방식 데이터 생성 시작")
    print(f"{'='*60}")
    print(f"총 레코드 수: {total_records:,}")
    print(f"배치 크기: {batch_size:,}")
    print(f"데이터베이스: {db_url.split('@')[1] if '@' in db_url else db_url}")
    print(f"{'='*60}\n")

    engine = create_async_engine(db_url)

    # 테이블 존재 확인 및 생성
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS performance_test_data (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                category VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                view_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # 인덱스 생성
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_perf_test_title ON performance_test_data(title);
            CREATE INDEX IF NOT EXISTS ix_perf_test_category ON performance_test_data(category);
            CREATE INDEX IF NOT EXISTS ix_perf_category_status ON performance_test_data(category, status);
            CREATE INDEX IF NOT EXISTS ix_perf_created_at_status ON performance_test_data(created_at, status);
        """))

    start_time = time.time()
    inserted_count = 0

    async with engine.begin() as conn:
        try:
            for batch_start in range(0, total_records, batch_size):
                batch_end = min(batch_start + batch_size, total_records)
                batch_data = generate_batch(batch_start, batch_end - batch_start)

                await conn.execute(
                    text("""
                        INSERT INTO performance_test_data
                        (title, content, category, status, view_count, created_at, updated_at)
                        VALUES (:title, :content, :category, :status, :view_count, :created_at, :updated_at)
                    """),
                    batch_data
                )

                inserted_count += len(batch_data)
                progress = inserted_count / total_records * 100
                elapsed = time.time() - start_time
                rate = inserted_count / elapsed if elapsed > 0 else 0

                print(f"진행률: {progress:6.2f}% | "
                      f"삽입: {inserted_count:>8,}/{total_records:,} | "
                      f"속도: {rate:,.0f} rec/s | "
                      f"경과: {elapsed:.1f}s")

        except Exception as e:
            print(f"\n오류 발생: {e}")
            raise

    await engine.dispose()

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"완료!")
    print(f"{'='*60}")
    print(f"총 레코드: {inserted_count:,}")
    print(f"소요 시간: {elapsed:.2f}초")
    print(f"평균 속도: {inserted_count / elapsed:,.0f} records/sec")
    print(f"{'='*60}\n")


def clear_table(db_url: str):
    """테이블 데이터 삭제"""
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM performance_test_data"))
        count = result.scalar()
        print(f"기존 데이터 {count:,}건 삭제 중...")

        conn.execute(text("TRUNCATE TABLE performance_test_data RESTART IDENTITY"))
        conn.commit()
        print("테이블 초기화 완료")


def main():
    parser = argparse.ArgumentParser(description="성능 테스트용 데이터 생성 스크립트")
    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="비동기 방식으로 데이터 생성"
    )
    parser.add_argument(
        "--records",
        type=int,
        default=100000,
        help="생성할 레코드 수 (기본값: 100000)"
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=5000,
        help="배치 크기 (기본값: 5000)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="기존 데이터 삭제 후 생성"
    )
    parser.add_argument(
        "--db-host",
        type=str,
        default=None,
        help="데이터베이스 호스트 (기본값: 환경변수 또는 localhost)"
    )
    parser.add_argument(
        "--db-port",
        type=int,
        default=None,
        help="데이터베이스 포트 (기본값: 환경변수 또는 15432)"
    )

    args = parser.parse_args()

    # 데이터베이스 URL 구성
    db_host = args.db_host or os.getenv("POSTGRES_HOST", "localhost")
    db_port = args.db_port or int(os.getenv("POSTGRES_PORT", "15432"))
    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_password = os.getenv("POSTGRES_PASSWORD", "test")
    db_name = os.getenv("POSTGRES_DB", "fastapi_playground")

    sync_db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    async_db_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    print(f"\n데이터베이스 연결: {db_host}:{db_port}/{db_name}")

    # 기존 데이터 삭제
    if args.clear:
        try:
            clear_table(sync_db_url)
        except Exception as e:
            print(f"테이블 초기화 중 오류 (테이블이 없을 수 있음): {e}")

    # 데이터 생성
    if args.use_async:
        asyncio.run(async_bulk_insert(async_db_url, args.records, args.batch))
    else:
        sync_bulk_insert(sync_db_url, args.records, args.batch)


if __name__ == "__main__":
    main()
