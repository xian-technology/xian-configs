"""Immutable successor-height clocks for contracts that create timed positions."""

PROTOCOL_VERSION = 1
MAX_ANCHOR_WORK = 32
SYSTEM_TIME_KEEPER = "__time_checkpoints__"

protocol_version = Variable()
keeper_ready = Variable()
queue_head = Variable()
queue_tail = Variable()
next_job_id = Variable()

anchors = Hash(default_value=None)
pending_heights = Hash(default_value=None)
job_heights = Hash(default_value=None)
job_next = Hash(default_value=0)


@construct
def seed():
    protocol_version.set(PROTOCOL_VERSION)
    keeper_ready.set(False)
    queue_head.set(0)
    queue_tail.set(0)
    next_job_id.set(1)


def is_integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def require_protocol():
    version = protocol_version.get()
    assert is_integer(version) and version == PROTOCOL_VERSION, (
        "unsupported time checkpoint protocol"
    )


def current_height():
    height = block_num
    assert is_integer(height) and height > 0, "positive VM block height required"
    return height


def enqueue(height: int):
    job_id = next_job_id.get()
    next_job_id.set(job_id + 1)
    job_heights[job_id] = height
    pending_heights[height] = job_id
    tail = queue_tail.get()
    if tail == 0:
        queue_head.set(job_id)
    else:
        job_next[tail] = job_id
    queue_tail.set(job_id)


def finish_job(job_id: int, height: int):
    if anchors[height] is None:
        anchors[height] = now
    pending_heights[height] = None
    successor = job_next[job_id]
    queue_head.set(successor)
    if successor == 0:
        queue_tail.set(0)
    job_heights[job_id] = None
    job_next[job_id] = None


@export
def get_protocol_version():
    return protocol_version.get()


@export
def get_anchor(height: int):
    assert is_integer(height) and height > 0, "positive anchor height required"
    return anchors[height]


@export
def request_anchor():
    require_protocol()
    assert keeper_ready.get() is True, "time checkpoint keeper is not ready"
    height = current_height()
    if anchors[height] is not None or pending_heights[height] is not None:
        return height
    enqueue(height)
    return height


@export
def process_time_anchors(max_work: int = 32):
    assert ctx.caller == SYSTEM_TIME_KEEPER, "only the reserved time keeper can process"
    require_protocol()
    assert is_integer(max_work) and 0 < max_work <= MAX_ANCHOR_WORK, (
        "max_work must be between 1 and 32"
    )
    height = current_height()
    if keeper_ready.get() is not True:
        keeper_ready.set(True)
    processed = 0
    while processed < max_work:
        job_id = queue_head.get()
        if job_id == 0:
            break
        requested_height = job_heights[job_id]
        if requested_height >= height:
            break
        finish_job(job_id, requested_height)
        processed += 1
    return processed
