import asyncio
from zlib import crc32
import random
from reboot.aio.contexts import (
    ReaderContext,
    WriterContext,
    WorkflowContext,
    TransactionContext,
)
from reboot.aio.tasks import Loop
from datetime import timedelta
from arpa.v1.workers_rbt import (
    IsFrozenRequest,
    IsFrozenResponse,
    Worker,
    FreezeRequest,
    FreezeResponse,
    Workers,
    CompleteRequest,
    CompleteResponse,
    AddRequest,
    AddResponse,
    CreateRequest,
    DemoRequest,
    DemoResponse,
    CreateResponse,
    InitializeRequest,
    InitializeResponse,
    ListRequest,
    ListResponse,
    RemoveRequest,
    RemoveResponse,
    RunRequest,
    RunResponse,
    StartRequest,
    StartResponse,
    Status,
    StatusRequest,
    StatusResponse,
)

WORKERS_INDEX_ID = '(singleton)'


class WorkerServicer(Worker.Servicer):

    async def Create(
        self,
        context: TransactionContext,
        state: Worker.State,
        request: CreateRequest,
    ) -> CreateResponse:
        state.task_description = request.task_description

        # We may start this worker immediately (if no `start_delay_milliseconds`
        # is provided), or after some delay.
        delay = timedelta(milliseconds=request.start_delay_milliseconds)
        await self.lookup().schedule(when=delay).Start(context)

        # Register ourselves with the Workers index.
        await Workers.lookup(WORKERS_INDEX_ID).Add(
            context,
            worker_id=context.state_id,
        )

        print(f"{context.state_id}: not started")
        return CreateResponse()

    async def Start(
        self,
        context: WriterContext,
        state: Worker.State,
        request: StartRequest,
    ) -> StartResponse:
        print(f"{context.state_id}: in progress")
        state.status = Status.IN_PROGRESS

        # The actual work is long-running, so we'll do that in a workflow.
        await self.lookup().schedule().Run(context)

        return StartResponse()

    async def Status(
        self,
        context: ReaderContext,
        state: Worker.State,
        request: StatusRequest,
    ) -> StatusResponse:
        return StatusResponse(
            status=state.status,
            task_description=state.task_description,
        )

    async def _complete(self, context: WorkflowContext | TransactionContext,
                        state: Worker.State):
        state.status = Status.COMPLETED
        print(f"{context.state_id}: completed")

        # In 30 seconds, remove this worker from the Workers index.
        await Workers.lookup(WORKERS_INDEX_ID).idempotently('remove').schedule(
            when=timedelta(seconds=30)).Remove(context,
                                               worker_id=context.state_id)

    async def Run(
        self,
        context: WorkflowContext,
        request: RunRequest,
    ) -> RunResponse | Loop:
        # Pretend that this worker is doing some work that takes a while.
        random_delay = timedelta(milliseconds=random.randint(1000, 20000))
        await asyncio.sleep(random_delay.total_seconds())

        # Update the worker's status to a 'done' state.
        async def complete_or_fail(state: Worker.State):
            # Toss a coin: 8 out of 10 times the task completes, but 2 out of 10 times it fails.
            # We can't toss the coin completely randomly, because then if we retry this workflow
            # it may make a different decision. Instead we'll hash the state ID.
            state_id_float_hash = str_to_float(context.state_id)
            if state_id_float_hash <= 0.2:
                state.status = Status.FAILED
                print(f"{context.state_id}: failed")
            else:
                await self._complete(context, state)

        await self.state.idempotently('complete_or_fail').write(
            context, complete_or_fail)

        latest_state = await self.state.read(context)

        return RunResponse()

    async def Complete(
        self,
        context: TransactionContext,
        state: Worker.State,
        request: CompleteRequest,
    ) -> CompleteResponse:
        await self._complete(context, state)
        # Wait a little moment so the frontend can show off call-in-progress rendering.
        await asyncio.sleep(1.0)
        return CompleteResponse()


class WorkersServicer(Workers.Servicer):

    async def Initialize(
        self,
        context: WriterContext,
        state: Workers.State,
        request: InitializeRequest,
    ) -> InitializeResponse:
        # We can start with an empty state.
        return InitializeResponse()

    async def Add(
        self,
        context: WriterContext,
        state: Workers.State,
        request: AddRequest,
    ) -> AddResponse:
        state.worker_ids.append(request.worker_id)
        return AddResponse()

    async def Remove(
        self,
        context: WriterContext,
        state: Workers.State,
        request: RemoveRequest,
    ) -> RemoveResponse:
        if request.worker_id in state.worker_ids:
            state.worker_ids.remove(request.worker_id)
        return RemoveResponse()

    async def List(
        self,
        context: ReaderContext,
        state: Workers.State,
        request: ListRequest,
    ) -> ListResponse:
        # For convenience by the caller, collect all of the worker's statuses in one response.
        workers_with_statuses: list[ListResponse.WorkerStatus] = []

        # Collect all of those in parallel, for a quicker result.
        async def get_status(worker_id: str):
            worker = Worker.lookup(worker_id)
            response = await worker.Status(context)
            workers_with_statuses.append(
                ListResponse.WorkerInfo(
                    worker_id=worker_id,
                    task_description=response.task_description,
                    status=response.status,
                ))

        await asyncio.gather(
            *[get_status(worker_id) for worker_id in state.worker_ids])

        return ListResponse(workers=workers_with_statuses)

    async def Demo(
        self,
        context: WorkflowContext,
        request: DemoRequest,
    ) -> Loop:
        latest_state = await self.state.read(context)
        if latest_state.frozen:
            return Loop(when=timedelta(seconds=5))

        # If this is the first iteration, create a few new worker straight away. Otherwise, just create one.
        num_workers_to_create = 1
        if context.iteration == 0:
            num_workers_to_create = 5

        for i in range(num_workers_to_create):
            VERBS = [
                'debug', 'refactor', 'optimize', 'deploy', 'code', 'reboot'
            ]
            ADJECTIVES = [
                "brilliant", "radiant", "magnificent", "benevolent",
                "gracious", "joyful", "resilient", "harmonious", "admirable",
                "charismatic"
            ]
            NOUNS = [
                "algorithm", "bandwidth", "cache", "database", "firewall",
                "keyboard", "motherboard", "processor", "software",
                "automated agent"
            ]
            task_description = f"{random.choice(VERBS)} the {random.choice(ADJECTIVES)} {random.choice(NOUNS)}"
            start_delay_milliseconds = random.randint(0, 5000)
            worker, _ = await Worker.construct().idempotently(
                f'create-{context.iteration}-{i}').Create(
                    context,
                    task_description=task_description,
                    start_delay_milliseconds=start_delay_milliseconds,
                )

        # Do this every 1-10 seconds.
        return Loop(when=timedelta(seconds=5))

    async def Freeze(
        self,
        context: WriterContext,
        state: Workers.State,
        request: FreezeRequest,
    ) -> FreezeResponse:
        if request.frozen:
            print("freezing worker creation!")
        else:
            print("unfreezing worker creation!")
        state.frozen = request.frozen
        return FreezeResponse()

    async def IsFrozen(
        self,
        context: ReaderContext,
        state: Workers.State,
        request: IsFrozenRequest,
    ) -> IsFrozenResponse:
        return IsFrozenResponse(frozen=state.frozen)


def bytes_to_float(b):
    return float(crc32(b) & 0xffffffff) / 2**32


def str_to_float(s, encoding="utf-8"):
    return bytes_to_float(s.encode(encoding))
