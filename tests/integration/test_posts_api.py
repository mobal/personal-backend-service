import random
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from tests.helpers.utils import generate_jwt_token

from app.models.post import Post
from app.schemas.post_schema import MAX_TITLE_LENGTH, CreatePost
from app.services.attachment_service import AttachmentService
from app.services.publisher_service import PublisherService
from app.services.s3_storage_service import S3StorageService

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
    def setup_function(
        self,
        initialize_posts_table,
    ):
        pass

    def test_successfully_get_posts(self, posts: list[Post], test_client: TestClient):
        response = test_client.get(BASE_URL)

        assert response.status_code == status.HTTP_200_OK
        for post_response in response.json()["posts"]:
            post = next(post for post in posts if post.id == post_response["id"])
            assert post_response.items() <= post.model_dump(by_alias=True).items()

    def test_get_posts_returns_newest_first(
        self, posts: list[Post], posts_table, test_client: TestClient
    ):
        now = datetime.now(UTC)
        for age_in_days, post in enumerate(random.sample(posts, len(posts))):
            posts_table.update_item(
                Key={"id": post.id},
                UpdateExpression="SET published_at = :published_at",
                ExpressionAttributeValues={
                    ":published_at": (now - timedelta(days=age_in_days)).isoformat()
                },
            )

        response = test_client.get(BASE_URL)

        published = [post["publishedAt"] for post in response.json()["posts"]]
        assert len(published) == len(posts)
        assert published == sorted(published, reverse=True)

    def test_fail_to_get_post_by_uuid_due_to_not_found(
        self, posts: list[Post], test_client: TestClient
    ):
        response = test_client.get(f"{BASE_URL}/{str(uuid.uuid4())}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert {
            "status": status.HTTP_404_NOT_FOUND,
            "message": ERROR_MESSAGE_NOT_FOUND,
        }.items() <= response.json().items()

    def test_fail_to_get_future_post_by_uuid(
        self, posts: list[Post], test_client: TestClient, posts_table
    ):
        future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        posts_table.update_item(
            Key={"id": posts[0].id},
            UpdateExpression="SET published_at = :published_at",
            ExpressionAttributeValues={":published_at": future},
        )

        response = test_client.get(f"{BASE_URL}/{posts[0].id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

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

    def test_successfully_get_archive(self, posts: list[Post], test_client: TestClient):
        response = test_client.get(f"{BASE_URL}/archive")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()[datetime.now(UTC).strftime("%Y-%m")] == len(posts)

    def test_successfully_get_empty_archive(self, test_client: TestClient, posts_table):
        for item in posts_table.scan()["Items"]:
            posts_table.delete_item(Key={"id": item["id"]})

        response = test_client.get(f"{BASE_URL}/archive")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {}

    def test_successfully_get_post_by_post_path(
        self, posts: list[Post], test_client: TestClient
    ):
        now = datetime.now(UTC)
        response = test_client.get(
            f"{BASE_URL}/{now.strftime('%Y/%m/%d')}/{posts[0].slug}"
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
        random_timestamp = random.uniform(
            datetime(1970, 1, 1, tzinfo=UTC).timestamp(),
            datetime(2100, 12, 31, tzinfo=UTC).timestamp(),
        )
        random_date = datetime.fromtimestamp(random_timestamp, UTC)

        response = test_client.get(
            f"{BASE_URL}/{random_date.strftime('%Y/%m/%d')}/slug"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert {
            "status": status.HTTP_404_NOT_FOUND,
            "message": ERROR_MESSAGE_NOT_FOUND,
        }.items() <= response.json().items()

    def test_fail_to_get_post_by_impossible_calendar_date(
        self, test_client: TestClient
    ):
        response = test_client.get(f"{BASE_URL}/2026/02/31/slug")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.fixture
    def make_unpublished(self, posts_table):
        def make(post_id: str, publication_state: str) -> None:
            if publication_state == "draft":
                posts_table.update_item(
                    Key={"id": post_id}, UpdateExpression="REMOVE published_at"
                )
            else:
                posts_table.update_item(
                    Key={"id": post_id},
                    UpdateExpression="SET published_at = :published_at",
                    ExpressionAttributeValues={
                        ":published_at": (
                            datetime.now(UTC) + timedelta(days=1)
                        ).isoformat()
                    },
                )

        return make

    @pytest.mark.parametrize("publication_state", ["draft", "scheduled"])
    def test_authenticated_read_returns_an_unpublished_post(
        self,
        publication_state: str,
        jwt_secret_ssm_param_value: str,
        make_unpublished,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        make_unpublished(posts[0].id, publication_state)
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.get(
            f"{BASE_URL}/{posts[0].id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == posts[0].id

    @pytest.mark.parametrize("publication_state", ["draft", "scheduled"])
    def test_anonymous_read_still_hides_an_unpublished_post(
        self,
        publication_state: str,
        make_unpublished,
        posts: list[Post],
        test_client: TestClient,
    ):
        make_unpublished(posts[0].id, publication_state)

        response = test_client.get(f"{BASE_URL}/{posts[0].id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_authenticated_read_still_hides_a_deleted_post(
        self,
        jwt_secret_ssm_param_value: str,
        posts: list[Post],
        posts_table,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        posts_table.update_item(
            Key={"id": posts[0].id},
            UpdateExpression="SET deleted_at = :deleted_at",
            ExpressionAttributeValues={":deleted_at": datetime.now(UTC).isoformat()},
        )
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.get(
            f"{BASE_URL}/{posts[0].id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("authorization", ["Bearer not-a-jwt", HEADER_EMPTY_BEARER])
    def test_read_with_an_invalid_token_is_rejected(
        self,
        authorization: str,
        posts: list[Post],
        test_client: TestClient,
    ):
        response = test_client.get(
            f"{BASE_URL}/{posts[0].id}", headers={"Authorization": authorization}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_a_created_draft_can_be_read_from_its_location_header(
        self,
        create_post: CreatePost,
        jwt_secret_ssm_param_value: str,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)
        headers = {"Authorization": f"Bearer {jwt_token}"}
        created = test_client.post(
            BASE_URL,
            headers=headers,
            json=create_post.model_dump(by_alias=True) | {"publishedAt": None},
        )

        response = test_client.get(created.headers["Location"], headers=headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["title"] == create_post.title

    def test_fail_to_delete_post_due_to_not_found(
        self,
        jwt_secret_ssm_param_value: str,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

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
        jwt_secret_ssm_param_value: str,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.delete(
            f"{BASE_URL}/{posts[0].id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_post_cleans_up_its_attachments_and_published_file(
        self,
        jwt_secret_ssm_param_value: str,
        mocker: MockerFixture,
        post_with_attachment: Post,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        delete_attachments = mocker.patch.object(
            AttachmentService, "delete_attachments"
        )
        remove_published = mocker.patch.object(PublisherService, "remove_published")
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.delete(
            f"{BASE_URL}/{post_with_attachment.id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        for cleanup in (delete_attachments, remove_published):
            cleanup.assert_called_once()
            assert cleanup.call_args.args[0].id == post_with_attachment.id

    def test_delete_post_succeeds_when_the_cleanup_fails(
        self,
        jwt_secret_ssm_param_value: str,
        mocker: MockerFixture,
        post_with_attachment: Post,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        mocker.patch.object(
            S3StorageService, "delete_object", side_effect=RuntimeError("s3 down")
        )
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.delete(
            f"{BASE_URL}/{post_with_attachment.id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert (
            test_client.get(f"{BASE_URL}/{post_with_attachment.id}").status_code
            == status.HTTP_404_NOT_FOUND
        )

    def test_delete_post_does_not_clean_up_a_post_that_was_not_found(
        self,
        jwt_secret_ssm_param_value: str,
        mocker: MockerFixture,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        delete_attachments = mocker.patch.object(
            AttachmentService, "delete_attachments"
        )
        remove_published = mocker.patch.object(PublisherService, "remove_published")
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.delete(
            f"{BASE_URL}/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        delete_attachments.assert_not_called()
        remove_published.assert_not_called()

    def test_fail_to_create_post_due_to_bad_request(
        self,
        jwt_secret_ssm_param_value: str,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.post(
            BASE_URL, headers={"Authorization": f"Bearer {jwt_token}"}, json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

        result = response.json()
        assert result["status"] == status.HTTP_422_UNPROCESSABLE_CONTENT
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
        jwt_secret_ssm_param_value: str,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_post.model_dump(by_alias=True),
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.headers["Location"]

    def test_successfully_create_draft_without_published_at(
        self,
        create_post: CreatePost,
        jwt_secret_ssm_param_value: str,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)
        payload = create_post.model_dump(by_alias=True)
        payload.pop("publishedAt")

        response = test_client.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=payload,
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.headers["Location"]

    def test_fail_to_create_post_due_to_already_exists_by_title(
        self,
        jwt_secret_ssm_param_value: str,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=CreatePost(**posts[0].model_dump()).model_dump(by_alias=True),
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_fail_to_create_post_due_to_colliding_post_path(
        self,
        create_post: CreatePost,
        jwt_secret_ssm_param_value: str,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)
        headers = {"Authorization": f"Bearer {jwt_token}"}
        payload = create_post.model_dump(by_alias=True)

        first = test_client.post(
            BASE_URL, headers=headers, json=payload | {"title": "Hello World"}
        )
        second = test_client.post(
            BASE_URL, headers=headers, json=payload | {"title": "Hello, World!"}
        )

        assert first.status_code == status.HTTP_201_CREATED
        assert second.status_code == status.HTTP_409_CONFLICT

    def test_fail_to_create_post_with_title_that_has_no_slug(
        self,
        create_post: CreatePost,
        jwt_secret_ssm_param_value: str,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_post.model_dump(by_alias=True) | {"title": "?!?!"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_fail_to_create_post_with_oversized_title(
        self,
        create_post: CreatePost,
        jwt_secret_ssm_param_value: str,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_post.model_dump(by_alias=True)
            | {"title": "t" * (MAX_TITLE_LENGTH + 1)},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert response.json()["errors"][0]["loc"] == ["body", "title"]

    def test_fail_to_update_title_due_to_colliding_post_path(
        self,
        jwt_secret_ssm_param_value: str,
        posts: list[Post],
        posts_table,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)
        headers = {"Authorization": f"Bearer {jwt_token}"}
        renamed = test_client.put(
            f"{BASE_URL}/{posts[0].id}", headers=headers, json={"title": "Hello World"}
        )

        response = test_client.put(
            f"{BASE_URL}/{posts[1].id}",
            headers=headers,
            json={"title": "Hello, World!"},
        )

        assert renamed.status_code == status.HTTP_204_NO_CONTENT
        assert response.status_code == status.HTTP_409_CONFLICT
        stored = posts_table.get_item(Key={"id": posts[1].id})["Item"]
        assert stored["title"] == posts[1].title

    def test_fail_to_update_post_due_to_not_found(
        self,
        create_post: CreatePost,
        jwt_secret_ssm_param_value: str,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

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
        jwt_secret_ssm_param_value: str,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

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

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

        result = response.json()
        assert result["status"] == status.HTTP_422_UNPROCESSABLE_CONTENT
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
        jwt_secret_ssm_param_value: str,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.put(
            f"{BASE_URL}/{posts[0].id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=posts[0].model_dump(),
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_successfully_unpublish_post(
        self,
        jwt_secret_ssm_param_value: str,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.put(
            f"{BASE_URL}/{posts[0].id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={"publishedAt": None},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert (
            test_client.get(f"{BASE_URL}/{posts[0].id}").status_code
            == status.HTTP_404_NOT_FOUND
        )

    def test_successfully_publish_post(
        self,
        mocker,
        jwt_secret_ssm_param_value: str,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)
        publish = mocker.patch.object(PublisherService, "publish")

        response = test_client.post(
            f"{BASE_URL}/{posts[0].id}/publish",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        publish.assert_called_once_with(posts[0].id)

    def test_fail_to_update_post_due_to_empty_body(
        self,
        jwt_secret_ssm_param_value: str,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.put(
            f"{BASE_URL}/{posts[0].id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.parametrize("field", ["author", "title", "content", "tags", "meta"])
    def test_fail_to_update_post_due_to_null_required_field(
        self,
        field: str,
        jwt_secret_ssm_param_value: str,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.put(
            f"{BASE_URL}/{posts[0].id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={field: None},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert (
            test_client.get(f"{BASE_URL}/{posts[0].id}").status_code
            == status.HTTP_200_OK
        )

    def test_fail_expired_jwt_token_cause_forbidden(
        self,
        posts: list[Post],
        user_dict: dict[str, str | None],
        jwt_secret_ssm_param_value: str,
        test_client: TestClient,
    ):
        import jwt

        expired_token = jwt.encode(
            {"sub": user_dict.get("email"), "exp": 0},
            jwt_secret_ssm_param_value,
            algorithm="HS256",
        )

        response = test_client.delete(
            f"{BASE_URL}/{posts[0].id}",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["message"] == ERROR_MESSAGE_NOT_AUTHENTICATED
