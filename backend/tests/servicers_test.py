import sys

print("PYTHONPATH: ", sys.path)

import asyncio
import unittest
from arpa.v1.workers_rbt import Worker, Workers, Status
from servicers import WorkerServicer, WorkersServicer, WORKERS_INDEX_ID
from reboot.aio.tests import Reboot


def is_done(status: Status.ValueType) -> bool:
    return status == Status.COMPLETED or status == Status.FAILED


def is_started(status: Status.ValueType) -> bool:
    return status == Status.IN_PROGRESS or is_done(status)


class TestWorker(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.rbt = Reboot()
        await self.rbt.start()

    async def asyncTearDown(self) -> None:
        await self.rbt.stop()

    async def test_one_lifecycle(self) -> None:
        await self.rbt.up(servicers=[WorkerServicer, WorkersServicer])

        context = self.rbt.create_external_context(
            name="TestWorker.test_basic")

        # We must have initialized the Workers index.
        workers, _ = await Workers.construct(id=WORKERS_INDEX_ID
                                             ).Initialize(context)

        # Create a worker.
        worker, _ = await Worker.construct().Create(context)

        # The worker is listed in the Workers index.
        response = await workers.List(context)
        self.assertEqual(len(response.workers), 1)
        self.assertEqual(response.workers[0].worker_id, worker.state_id)

        # We can reactively listen for changes to the workers.
        async for response in workers.reactively().List(context):
            self.assertEqual(len(response.workers), 1)
            self.assertEqual(response.workers[0].worker_id, worker.state_id)
            # The worker will soon be started, and eventually finish.
            print("Reactive update:"
                  f"worker status is now {response.workers[0].status}")
            if is_done(response.workers[0].status):
                break
