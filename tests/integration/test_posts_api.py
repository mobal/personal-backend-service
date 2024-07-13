import random
import uuid

import jwt
import pendulum
import pytest
from fastapi.testclient import TestClient
from httpx import ConnectTimeout, Response
from respx import MockRouter, Route
from starlette import status

from app.main import app
from app.middlewares import COUNTRY_IS_API_BASE_URL
from app.models.post import Post
from app.schemas.post_schema import CreatePost

BASE_URL = "/api/v1/posts"
CACHE_SERVICE_URL = f"{pytest.cache_service_base_url}/api/cache"
ERROR_MESSAGE_FORBIDDEN = "Forbidden"
ERROR_MESSAGE_INTERNAL_SERVER_ERROR = "Internal server error"
ERROR_MESSAGE_NOT_AUTHENTICATED = "Not authenticated"
ERROR_MESSAGE_NOT_AUTHORIZED = "Not authorized"
ERROR_MESSAGE_NOT_FOUND = "The requested post was not found"
HEADER_EMPTY_BEARER = "Bearer "
ROLE_POST_CREATE = "post:create"
ROLE_POST_DELETE = "post:delete"
ROLE_POST_EDIT = "post:edit"


@pytest.mark.asyncio
class TestPostsApi:
    async def __assert_response(
        self,
        route_mock: Route,
        message: str,
        status_code: int,
        response: Response,
    ):
        assert response.status_code == status_code

        assert {
            "status": status_code,
            "message": message,
        }.items() <= response.json().items()
        assert route_mock.called
        assert route_mock.call_count == 1

    async def __generate_jwt_token(self, roles: list[str], exp: int = 1) -> (str, str):
        iat = pendulum.now()
        exp = iat.add(hours=exp)
        token_id = str(uuid.uuid4())
        return (
            jwt.encode(
                {
                    "exp": exp.int_timestamp,
                    "iat": iat.int_timestamp,
                    "jti": token_id,
                    "sub": {"id": str(uuid.uuid4()), "roles": roles},
                },
                pytest.jwt_secret,
            ),
            token_id,
        )

    async def __generate_respx_mock(
        self,
        method: str,
        response: Response,
        respx_mock: MockRouter,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> Route:
        return respx_mock.route(
            headers=headers, method=method, url__startswith=url
        ).mock(response)

    @pytest.fixture
    async def cache_service_response_200(self) -> Response:
        jwt_token, token_id = await self.__generate_jwt_token(
            [ROLE_POST_CREATE, ROLE_POST_DELETE, ROLE_POST_EDIT]
        )
        return Response(
            status_code=status.HTTP_200_OK,
            json={
                "key": f"jti_{token_id}",
                "value": jwt_token,
                "createdAt": pendulum.now().to_iso8601_string(),
            },
        )

    @pytest.fixture
    async def cache_service_response_403(self) -> Response:
        return Response(
            status_code=status.HTTP_403_FORBIDDEN,
            json={
                "status": status.HTTP_403_FORBIDDEN,
                "id": str(uuid.uuid4()),
                "message": ERROR_MESSAGE_NOT_AUTHENTICATED,
            },
        )

    @pytest.fixture
    async def cache_service_response_404(self) -> Response:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            json={
                "status": status.HTTP_404_NOT_FOUND,
                "id": str(uuid.uuid4()),
                "message": "Not found",
            },
        )

    @pytest.fixture
    async def cache_service_response_500(self) -> Response:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            json={
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "id": str(uuid.uuid4()),
                "message": "Internal server error",
            },
        )

    @pytest.fixture
    async def create_post(self, make_post) -> CreatePost:
        post = make_post()
        return CreatePost(
            author=post.author,
            title=post.title,
            content=post.content,
            tags=post.tags,
            meta=post.meta.model_dump(),
            published_at=post.published_at,
        )

    @pytest.fixture(autouse=True)
    async def setup_function(self, respx_mock: MockRouter):
        await self.__generate_respx_mock(
            "GET",
            Response(
                status_code=status.HTTP_200_OK,
                json={
                    "ip": "8.8.8.8",
                    "country": "US",
                },
            ),
            respx_mock,
            COUNTRY_IS_API_BASE_URL,
        )

    @pytest.fixture
    def test_client(self, initialize_posts_table) -> TestClient:
        return TestClient(app, raise_server_exceptions=False)

    async def test_successfully_get_posts(
        self, posts: list[Post], test_client: TestClient
    ):
        response = test_client.get(BASE_URL)

        assert response.status_code == status.HTTP_200_OK
        for post_response in response.json()["data"]:
            post = next(post for post in posts if post.id == post_response["id"])
            assert post_response.items() <= post.model_dump(by_alias=True).items()

    async def test_fail_to_get_post_by_uuid_due_to_not_found(
        self, posts: list[Post], test_client: TestClient
    ):
        response = test_client.get(f"{BASE_URL}/653000ce-4b15-4242-a07d-fd8eed656d36")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert {
            "status": status.HTTP_404_NOT_FOUND,
            "message": ERROR_MESSAGE_NOT_FOUND,
        }.items() <= response.json().items()

    async def test_successfully_get_post_by_uuid(
        self, posts: list[Post], test_client: TestClient
    ):
        response = test_client.get(f"{BASE_URL}/{posts[0].id}")

        assert response.status_code == status.HTTP_200_OK
        assert (
            posts[0]
            .model_dump(
                exclude={"content", "created_at", "deleted_at", "post_path"},
                by_alias=True,
            )
            .items()
            <= response.json().items()
        )

    async def test_fail_to_get_post_due_to_invalid_client(
        self,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        route_mock = await self.__generate_respx_mock(
            "GET",
            Response(
                status_code=status.HTTP_200_OK,
                json={
                    "ip": "testclient",
                    "country": "RU",
                },
            ),
            respx_mock,
            COUNTRY_IS_API_BASE_URL,
        )

        response = test_client.get(f"{BASE_URL}/{str(uuid.uuid4())}")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {"message": ERROR_MESSAGE_FORBIDDEN}
        assert route_mock.called
        assert route_mock.call_count == 1

    async def test_successfully_get_post_despite_country_api_unavailability(
        self,
        posts: list[Post],
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        route_mock = respx_mock.route(
            method="GET", url__startswith=COUNTRY_IS_API_BASE_URL
        ).mock(side_effect=ConnectTimeout("timeout"))

        response = test_client.get(f"{BASE_URL}/{posts[0].id}")

        assert response.status_code == status.HTTP_200_OK
        assert (
            posts[0]
            .model_dump(
                exclude={"content", "created_at", "deleted_at", "post_path"},
                by_alias=True,
            )
            .items()
            <= response.json().items()
        )
        assert route_mock.called
        assert route_mock.call_count == 1

    async def test_successfully_get_archive(
        self, posts: list[Post], test_client: TestClient
    ):
        response = test_client.get(f"{BASE_URL}/archive")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()[pendulum.now().format("YYYY-MM")] == len(posts)

    async def test_successfully_get_post_by_post_path(
        self, posts: list[Post], test_client: TestClient
    ):
        now = pendulum.now()
        response = test_client.get(
            f"{BASE_URL}/{now.year}/{now.month}/{now.day}/{posts[0].slug}"
        )

        assert response.status_code == status.HTTP_200_OK
        assert (
            posts[0]
            .model_dump(
                exclude={"content", "created_at", "deleted_at", "post_path"},
                by_alias=True,
            )
            .items()
            <= response.json().items()
        )

    async def test_fail_to_get_post_by_date_and_slug_due_to_not_found(
        self, test_client: TestClient
    ):
        response = test_client.get(
            f"{BASE_URL}/{random.randint(1970, 2999)}/{random.randint(3, 12)}/{random.randint(1, 30)}/slug"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert {
            "status": status.HTTP_404_NOT_FOUND,
            "message": ERROR_MESSAGE_NOT_FOUND,
        }.items() <= response.json().items()

    async def test_fail_to_delete_post_due_to_not_found(
        self,
        cache_service_response_404: Response,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_DELETE])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_404,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.delete(
            f"{BASE_URL}/{str(uuid.uuid4())}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        await self.__assert_response(
            cache_service_mock,
            ERROR_MESSAGE_NOT_FOUND,
            status.HTTP_404_NOT_FOUND,
            response,
        )

    async def test_fail_to_delete_post_due_to_unauthorized(
        self, test_client: TestClient
    ):
        response = test_client.delete(
            f"{BASE_URL}/{str(uuid.uuid4())}",
            headers={"Authorization": HEADER_EMPTY_BEARER},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert {
            "status": status.HTTP_403_FORBIDDEN,
            "message": ERROR_MESSAGE_NOT_AUTHENTICATED,
        }.items() <= response.json().items()

    async def test_fail_to_delete_post_due_to_blacklisted_jwt_token(
        self,
        cache_service_response_200: Response,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_DELETE])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_200,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.delete(
            f"{BASE_URL}/{str(uuid.uuid4())}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        await self.__assert_response(
            cache_service_mock,
            ERROR_MESSAGE_NOT_AUTHENTICATED,
            status.HTTP_403_FORBIDDEN,
            response,
        )

    async def test_fail_to_delete_post_due_to_missing_privileges(
        self,
        cache_service_response_404: Response,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_CREATE])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_404,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.delete(
            f"{BASE_URL}/{str(uuid.uuid4())}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        await self.__assert_response(
            cache_service_mock,
            ERROR_MESSAGE_NOT_AUTHORIZED,
            status.HTTP_401_UNAUTHORIZED,
            response,
        )

    async def test_fail_to_delete_post_due_to_unexpected_cache_service_exception(
        self,
        cache_service_response_500: Response,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_CREATE])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_500,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.delete(
            f"{BASE_URL}/{str(uuid.uuid4())}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        await self.__assert_response(
            cache_service_mock,
            ERROR_MESSAGE_INTERNAL_SERVER_ERROR,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            response,
        )

    async def test_successfully_delete_post(
        self,
        cache_service_response_404: Response,
        posts: list[Post],
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_DELETE])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_404,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.delete(
            f"{BASE_URL}/{posts[0].id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_create_post_due_to_bad_request(
        self,
        cache_service_response_404,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_CREATE])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_404,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.post(
            BASE_URL, headers={"Authorization": f"Bearer {jwt_token}"}, json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        result = response.json()
        assert result["status"] == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert result["id"]
        assert result["message"]
        assert result["errors"]
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_create_post_due_to_unauthorized(
        self,
        create_post: CreatePost,
        test_client: TestClient,
    ):
        response = test_client.post(
            BASE_URL,
            headers={"Authorization": HEADER_EMPTY_BEARER},
            json=create_post.model_dump(by_alias=True),
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert {
            "status": status.HTTP_403_FORBIDDEN,
            "message": ERROR_MESSAGE_NOT_AUTHENTICATED,
        }.items() <= response.json().items()

    async def test_fail_to_create_post_due_to_blacklisted_jwt_token(
        self,
        cache_service_response_200: Response,
        create_post: CreatePost,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_CREATE])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_200,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_post.model_dump(by_alias=True),
        )

        await self.__assert_response(
            cache_service_mock,
            ERROR_MESSAGE_NOT_AUTHENTICATED,
            status.HTTP_403_FORBIDDEN,
            response,
        )

    async def test_fail_to_create_post_due_to_missing_privileges(
        self,
        cache_service_response_404: Response,
        create_post: CreatePost,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_DELETE])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_404,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_post.model_dump(by_alias=True),
        )

        await self.__assert_response(
            cache_service_mock,
            ERROR_MESSAGE_NOT_AUTHORIZED,
            status.HTTP_401_UNAUTHORIZED,
            response,
        )

    async def test_fail_to_create_post_due_to_unexpected_cache_service_exception(
        self,
        cache_service_response_500: Response,
        create_post: CreatePost,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_DELETE])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_500,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_post.model_dump(by_alias=True),
        )

        await self.__assert_response(
            cache_service_mock,
            ERROR_MESSAGE_INTERNAL_SERVER_ERROR,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            response,
        )

    async def test_successfully_create_post(
        self,
        cache_service_response_404: Response,
        create_post: CreatePost,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_CREATE])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_404,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_post.model_dump(by_alias=True),
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.headers["Location"]
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_create_post_due_to_already_exists_by_title(
        self,
        cache_service_response_404: Response,
        posts: list[Post],
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_CREATE])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_404,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=CreatePost(**posts[0].model_dump()).model_dump(by_alias=True),
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_update_post_due_to_not_found(
        self,
        cache_service_response_404: Response,
        create_post: CreatePost,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_EDIT])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_404,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.put(
            f"{BASE_URL}/{str(uuid.uuid4())}",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_post.model_dump(by_alias=True),
        )

        await self.__assert_response(
            cache_service_mock,
            ERROR_MESSAGE_NOT_FOUND,
            status.HTTP_404_NOT_FOUND,
            response,
        )

    async def test_fail_to_update_post_due_to_bad_request(
        self,
        cache_service_response_404,
        posts: list[Post],
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_EDIT])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_404,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.put(
            f"{BASE_URL}/{posts[0].id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={
                "author": "a",
                "title": "t",
                "content": "c",
                "tags": [],
                "published_at": 0,
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        result = response.json()
        assert result["status"] == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert result["id"]
        assert result["message"]
        assert result["errors"]
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_update_post_due_to_unauthorized(
        self,
        create_post: CreatePost,
        test_client: TestClient,
    ):
        response = test_client.put(
            f"{BASE_URL}/{str(uuid.uuid4())}",
            headers={"Authorization": HEADER_EMPTY_BEARER},
            json=create_post.model_dump(by_alias=True),
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert {
            "status": status.HTTP_403_FORBIDDEN,
            "message": ERROR_MESSAGE_NOT_AUTHENTICATED,
        }.items() <= response.json().items()

    async def test_fail_to_update_post_due_to_blacklisted_jwt_token(
        self,
        cache_service_response_200: Response,
        create_post: CreatePost,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_DELETE])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_200,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.put(
            f"{BASE_URL}/{str(uuid.uuid4())}",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_post.model_dump(by_alias=True),
        )

        await self.__assert_response(
            cache_service_mock,
            ERROR_MESSAGE_NOT_AUTHENTICATED,
            status.HTTP_403_FORBIDDEN,
            response,
        )

    async def test_fail_to_update_post_due_to_missing_privileges(
        self,
        cache_service_response_404: Response,
        create_post: CreatePost,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_DELETE])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_404,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.put(
            f"{BASE_URL}/{str(uuid.uuid4())}",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_post.model_dump(by_alias=True),
        )

        await self.__assert_response(
            cache_service_mock,
            ERROR_MESSAGE_NOT_AUTHORIZED,
            status.HTTP_401_UNAUTHORIZED,
            response,
        )

    async def test_fail_to_update_post_due_to_unexpected_cache_service_exception(
        self,
        cache_service_response_500: Response,
        create_post: CreatePost,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_DELETE])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_500,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.put(
            f"{BASE_URL}/{str(uuid.uuid4())}",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_post.model_dump(by_alias=True),
        )

        await self.__assert_response(
            cache_service_mock,
            ERROR_MESSAGE_INTERNAL_SERVER_ERROR,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            response,
        )

    async def test_successfully_update_post(
        self,
        cache_service_response_404: Response,
        posts: list[Post],
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await self.__generate_jwt_token([ROLE_POST_EDIT])
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_404,
            respx_mock,
            CACHE_SERVICE_URL,
        )
        response = test_client.put(
            f"{BASE_URL}/{posts[0].id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=posts[0].model_dump(),
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1
