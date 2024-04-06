from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

"""
create_engine, sessionmaker 등을 사용하는것은 SQLAlchemy 데이터베이스를 사용하기 위해 따라야 할 규칙이다.

- autocommit=False
  데이터를 변경했을 때 commit 이라는 사인을 주어야만 실제 저장이 된다. 

- autocommit=True
  commit 없어도 즉시 데이터베이스에 변경사항이 적용된다. 

- autocommit=False
  데이터를 잘못 저장했을 경우 rollback 으로 되돌리는 것이 가능하다. 

- autocommit=True
  commit이 필요없는 것처럼 rollback도 동작하지 않는다.
"""

SQLALCHEMY_DATABASE_URL = "mysql+mysqlconnector://root:test@localhost:13306/fastapi_playground"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
