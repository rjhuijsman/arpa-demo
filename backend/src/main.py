import asyncio
import logging

from arpa.v1.workers_rbt import Worker, Workers
from reboot.aio.applications import Application
from reboot.aio.external import ExternalContext
from servicers import WORKERS_INDEX_ID, WorkerServicer, WorkersServicer

logging.basicConfig(level=logging.INFO)


async def initialize(context: ExternalContext):
    # Initialize the `Workers` index that we'll use to keep track of all of our workers.
    workers, _, = await Workers.construct(
        id=WORKERS_INDEX_ID).idempotently('initialize').Initialize(context)

    logging.info('👋 Our Workers are ready to go! 👋')

    # Start the demo worker generator.
    await workers.idempotently('demo').schedule().Demo(context)


async def main():
    await Application(
        servicers=[WorkerServicer, WorkersServicer],
        initialize=initialize,
    ).run()


if __name__ == '__main__':
    asyncio.run(main())
