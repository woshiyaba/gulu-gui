import asyncio

from common.utils import lkgc
from api.services import ops_service

async def main():
    return await ops_service.sync_pokemon_from_lkgc_for_ops({})
if __name__ == '__main__':
    import asyncio
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(
            asyncio.WindowsSelectorEventLoopPolicy()
        )
    result = asyncio.run(main())
    print(result)