from app.easytests import EasyTest
from app.tests.config import nextlike_easytest_config


class TestSimpleInjectDataAPI(EasyTest):
    config = nextlike_easytest_config

    async def get_cases(self):
        return [
            {"message": "hello world"},
        ]

    async def test(self, message):
        response = await  self.request(
            "get",
            "/api/health",
            expected_status=200,
        )
