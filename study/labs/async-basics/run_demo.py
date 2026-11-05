"""Show when a created asyncio Task gets a chance to run."""

import asyncio


async def child() -> None:
    print("child:start")
    await asyncio.sleep(0)
    print("child:end")


async def main() -> None:
    print("main:before-create")
    task = asyncio.create_task(child())
    print("main:after-create")

    await task
    print("main:after-await")


if __name__ == "__main__":
    asyncio.run(main())
