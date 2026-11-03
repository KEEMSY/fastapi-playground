import pytest
import asyncio

# 테스트 함수 간에 공유될 리스트
event_loops = []

@pytest.mark.asyncio
async def test_event_loop_1():
    """첫 번째 테스트에서 이벤트 루프 저장"""
    loop = asyncio.get_event_loop()
    event_loops.append(loop)
    
    print(f"\n테스트 1 이벤트 루프: {id(loop)}")
    assert asyncio.get_event_loop() is loop
    
@pytest.mark.asyncio
async def test_event_loop_2():
    """두 번째 테스트에서 같은 이벤트 루프인지 확인"""
    loop = asyncio.get_event_loop()
    
    print(f"\n테스트 2 이벤트 루프: {id(loop)}")
    
    # 이전 테스트와 같은 이벤트 루프인지 확인
    if event_loops:
        first_loop = event_loops[0]
        assert loop is first_loop, f"이벤트 루프가 다릅니다: {id(first_loop)} != {id(loop)}"
    else:
        pytest.fail("첫 번째 테스트가 실행되지 않았습니다") 