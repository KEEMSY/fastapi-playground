"""
pytest_asyncio 의 기본 event_loop fixture 는 scope 가 Function 이며,
이 때문에 매 번 테스트 함수가 실행될 때 마다 기존 루프가 닫히고 새로운 루프가 생겨 다른 테스트의 session is closed 문제 발생.
이를 해결하기 위해, 전체 테스트를 싱행하는 동안 Loop를 하나만 사용하도록 session scope 의 event loop fixture 를 새로 정의한다.

참고 자료
- https://stackoverflow.com/questions/61022713/pytest-asyncio-has-a-closed-event-loop-but-only-when-running-all-tests
- https://arc.net/l/quote/obnyijxk
"""


# 방법 1,
# @pytest_asyncio.fixture(autouse=True, scope="session")
# def event_loop():
#     try:
#         loop = asyncio.get_running_loop()
#     except RuntimeError:
#         loop = asyncio.new_event_loop()
#     yield loop
#     loop.close()

# 방법 2.
# @pytest.fixture
# def event_loop():
#     yield asyncio.get_event_loop()
#
# def pytest_sessionfinish(session, exitstatus):
#     asyncio.get_event_loop().close()


# 방법 3.
import asyncio
import pytest_asyncio


@pytest_asyncio.fixture(scope="module")
def event_loop():
    """Override pytest-asyncio's event loop fixture to session scope."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()