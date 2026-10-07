"""H07 回归：够线必须记成合格，衰减样不得被误放行，不许停在半开半关。"""
from rules import judge
from worker import claim_id


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class FakeConn:
    """最小假连接：SELECT 返回一行待处理扫描，UPDATE 记录写入内容。"""

    def __init__(self, row):
        self._row = row
        self.updates = []

    def transaction(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        if sql.lstrip().upper().startswith("SELECT"):
            return _Result(self._row)
        self.updates.append((sql, params or ()))
        return _Result(None)


def test_boundary_ff_is_qualified():
    verdict, reason = judge(0.72)
    assert verdict == "合格"
    assert reason


def test_above_line_is_qualified():
    verdict, _ = judge(0.78)
    assert verdict == "合格"


def test_below_line_is_degraded():
    verdict, _ = judge(0.61)
    assert verdict == "衰减"


def test_judge_never_leaves_half_state():
    for ff in (0.0, 0.5, 0.61, 0.719, 0.72, 0.8, 1.0):
        verdict, reason = judge(ff)
        assert verdict in ("合格", "衰减")
        assert reason


def test_claim_marks_done_and_qualified():
    conn = FakeConn({"id": 7, "fill_factor": 0.78})
    assert claim_id(conn, 7) is True
    assert len(conn.updates) == 1
    sql, params = conn.updates[0]
    assert "status='done'" in sql
    assert params[0] == "合格"
    assert params[1]


def test_claim_keeps_b_string_sample_degraded():
    conn = FakeConn({"id": 11, "fill_factor": 0.61})
    assert claim_id(conn, 11) is True
    sql, params = conn.updates[0]
    assert "status='done'" in sql
    assert params[0] == "衰减"


def test_claim_never_writes_back_pending():
    for ff in (0.61, 0.72, 0.9):
        conn = FakeConn({"id": 1, "fill_factor": ff})
        assert claim_id(conn, None) is True
        sql, params = conn.updates[0]
        assert "status='pending'" not in sql
        assert params[0] is not None


def test_claim_empty_queue_returns_false():
    conn = FakeConn(None)
    assert claim_id(conn, None) is False
    assert conn.updates == []
