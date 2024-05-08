from src.domains.async_example.presentation.schemas import CreateAsyncExample

"""
Request data 생성을 위한 스텝 클래스

[ 사용 주의 사항 ]
기준: Input, Output 모두 Pydantic Model을 사용하는 경우

1. "json=" 을 사용 하는 경우
res = await async_client.post(url="/TEST_URL", json=Request.json())
- json=Request.dict() 가능
- json=Request.model_dump() 가능
- json=Request.json() 불가능 -> <Response [422 Unprocessable Entity]> 반환
- json=Request.model_dump_json() 불가능 -> <Response [422 Unprocessable Entity]> 반환

2. "data=" 을 사용 하는 경우
res = await async_client.post(url="/TEST_URL", data=Request.json())
- data=Request.dict() 불가능 -> <Response [422 Unprocessable Entity]> 반환
- data=Request.model_dump() 뷸가능 -> <Response [422 Unprocessable Entity]> 반환
- data=Request.json() 가능
- data=Request.model_dump_json() 가능
"""


class AsyncExampleSteps:
    @staticmethod
    async def AsyncExample_생성요청(name, description):
        return CreateAsyncExample(
            name=name,
            description=description
        )
