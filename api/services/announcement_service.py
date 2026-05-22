from api.repositories import announcement_repository


async def get_announcement_like_count() -> int:
    return await announcement_repository.get_announcement_like_count()


async def like_announcement() -> int:
    return await announcement_repository.increment_announcement_like_count()
