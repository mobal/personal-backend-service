from typing import List

import pendulum

from app.api.v1.posts.models import Post


class PostService:
    def get_all_posts(self) -> List[Post]:
        post = self.get_post_by_uuid('8aad3ce9-fbae-48b5-8a40-3d7b3c501df9')
        return [post]

    def get_post_by_uuid(self, uuid: str) -> Post:
        return Post(uuid=uuid, author='Cicero', title='Lorem ipsum', content='Lorem ipsum',
                    created_at=pendulum.now('Europe/Budapest'), deleted_at=None, updated_at=None)
