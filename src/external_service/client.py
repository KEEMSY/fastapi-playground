import httpx

from src.external_service.schemas import PublicAPIsResponse


class Client:
    """
    public API service client
    public API를 반환하는 서비스의 클라이언트입니다.
    - get_public_apis: public API 목록을 반환합니다.
    - 사용:

    """

    BASE_URL: str = "https://api.publicapis.org"

    @property
    def client(self):
        return httpx.AsyncClient(base_url=self.BASE_URL, timeout=10.0)

    async def get_public_apis(self) -> PublicAPIsResponse:
        async with self.client as client:
            response = await client.get("/entries")

            return PublicAPIsResponse.model_validate_json(response.json())
