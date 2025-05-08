import random
import uuid

import pendulum
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import ConnectTimeout, Response
from respx import MockRouter

from app.middlewares import COUNTRY_IS_API_BASE_URL, banned_hosts
from app.models.post import Post
from app.schemas.post_schema import CreatePost
from tests.helpers.utils import generate_jwt_token

BASE_URL = "/api/v1/posts"
ERROR_MESSAGE_INTERNAL_SERVER_ERROR = "Internal Server Error"
ERROR_MESSAGE_NOT_AUTHENTICATED = "Not authenticated"
ERROR_MESSAGE_NOT_AUTHORIZED = "Not authorized"
ERROR_MESSAGE_NOT_FOUND = "The requested post was not found"
HEADER_EMPTY_BEARER = "Bearer "


class TestPostsApi:
    @pytest.fixture
    def create_post(self, make_post) -> CreatePost:
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
    def setup_function(self, respx_mock: MockRouter):
        banned_hosts.clear()
        respx_mock.route(method="GET", url__startswith=COUNTRY_IS_API_BASE_URL).mock(
            Response(
                status_code=status.HTTP_200_OK,
                json={
                    "ip": "8.8.8.8",
                    "country": "US",
                },
            ),
        )

    def test_successfully_get_posts(self, posts: list[Post], test_client: TestClient):
        response = test_client.get(BASE_URL)

        assert response.status_code == status.HTTP_200_OK
        for post_response in response.json()["posts"]:
            post = next(post for post in posts if post.id == post_response["id"])
            assert post_response.items() <= post.model_dump(by_alias=True).items()

    def test_fail_to_get_post_by_uuid_due_to_not_found(
        self, posts: list[Post], test_client: TestClient
    ):
        response = test_client.get(f"{BASE_URL}/{str(uuid.uuid4())}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert {
            "status": status.HTTP_404_NOT_FOUND,
            "message": ERROR_MESSAGE_NOT_FOUND,
        }.items() <= response.json().items()

    def test_successfully_get_post_by_uuid(
        self, posts: list[Post], test_client: TestClient
    ):
        response = test_client.get(f"{BASE_URL}/{posts[0].id}")

        assert response.status_code == status.HTTP_200_OK
        assert (
            posts[0]
            .model_dump(
                exclude={
                    "attachments",
                    "content",
                    "created_at",
                    "deleted_at",
                    "post_path",
                    "updated_at",
                },
                by_alias=True,
            )
            .items()
            <= response.json().items()
        )

    def test_fail_to_get_post_due_to_invalid_client(
        self,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        route_mock = respx_mock.route(
            method="GET",
            url__startswith=COUNTRY_IS_API_BASE_URL,
        ).mock(
            Response(
                status_code=status.HTTP_200_OK,
                json={
                    "ip": "testclient",
                    "country": "RU",
                },
            ),
        )

        response = test_client.get(f"{BASE_URL}/{str(uuid.uuid4())}")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {"message": "Forbidden"}
        assert route_mock.called
        assert route_mock.call_count == 1

    def test_successfully_get_post_despite_country_api_unavailability(
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
                exclude={
                    "attachments",
                    "content",
                    "created_at",
                    "deleted_at",
                    "post_path",
                    "updated_at",
                },
                by_alias=True,
            )
            .items()
            <= response.json().items()
        )
        assert route_mock.called
        assert route_mock.call_count == 1

    def test_successfully_get_archive(self, posts: list[Post], test_client: TestClient):
        response = test_client.get(f"{BASE_URL}/archive")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()[pendulum.now().format("YYYY-MM")] == len(posts)

    def test_successfully_get_post_by_post_path(
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
                exclude={
                    "attachments",
                    "content",
                    "created_at",
                    "deleted_at",
                    "post_path",
                },
                by_alias=True,
            )
            .items()
            <= response.json().items()
        )

    def test_fail_to_get_post_by_date_and_slug_due_to_not_found(
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

    def test_fail_to_delete_post_due_to_not_found(
        self,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(pytest.jwt_secret_ssm_param_value, user_dict)

        response = test_client.delete(
            f"{BASE_URL}/{str(uuid.uuid4())}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert {
            "status": status.HTTP_404_NOT_FOUND,
            "message": ERROR_MESSAGE_NOT_FOUND,
        }.items() <= response.json().items()

    def test_fail_to_delete_post_due_to_unauthorized(self, test_client: TestClient):
        response = test_client.delete(
            f"{BASE_URL}/{str(uuid.uuid4())}",
            headers={"Authorization": HEADER_EMPTY_BEARER},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert {
            "status": status.HTTP_403_FORBIDDEN,
            "message": ERROR_MESSAGE_NOT_AUTHENTICATED,
        }.items() <= response.json().items()

    def test_successfully_delete_post(
        self,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(pytest.jwt_secret_ssm_param_value, user_dict)

        response = test_client.delete(
            f"{BASE_URL}/{posts[0].id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_fail_to_create_post_due_to_bad_request(
        self,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(pytest.jwt_secret_ssm_param_value, user_dict)

        response = test_client.post(
            BASE_URL, headers={"Authorization": f"Bearer {jwt_token}"}, json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        result = response.json()
        assert result["status"] == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert result["id"]
        assert result["message"]
        assert result["errors"]

    def test_fail_to_create_post_due_to_unauthorized(
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

    def test_successfully_create_post(
        self,
        create_post: CreatePost,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(pytest.jwt_secret_ssm_param_value, user_dict)

        response = test_client.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_post.model_dump(by_alias=True),
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.headers["Location"]

    def test_fail_to_create_post_due_to_already_exists_by_title(
        self,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(pytest.jwt_secret_ssm_param_value, user_dict)

        response = test_client.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=CreatePost(**posts[0].model_dump()).model_dump(by_alias=True),
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_fail_to_update_post_due_to_not_found(
        self,
        create_post: CreatePost,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(pytest.jwt_secret_ssm_param_value, user_dict)

        response = test_client.put(
            f"{BASE_URL}/{str(uuid.uuid4())}",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_post.model_dump(by_alias=True),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert {
            "status": status.HTTP_404_NOT_FOUND,
            "message": ERROR_MESSAGE_NOT_FOUND,
        }.items() <= response.json().items()

    def test_fail_to_update_post_due_to_bad_request(
        self,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(pytest.jwt_secret_ssm_param_value, user_dict)

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

    def test_fail_to_update_post_due_to_unauthorized(
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

    def test_successfully_update_post(
        self,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(pytest.jwt_secret_ssm_param_value, user_dict)

        response = test_client.put(
            f"{BASE_URL}/{posts[0].id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=posts[0].model_dump(),
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
