"""
Document State Machine — Phase 1.6
管理文档生命周期：UPLOADED→PARSING→PARSED→CHUNKING→EMBEDDING→INDEXING→READY
"""

from enum import Enum
from typing import Optional

from loguru import logger


class DocState(str, Enum):
    UPLOADED = "UPLOADED"
    PARSING = "PARSING"
    PARSED = "PARSED"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    INDEXING = "INDEXING"
    READY = "READY"
    FAILED = "FAILED"
    DELETED = "DELETED"
    REINDEXING = "REINDEXING"


# Valid state transitions
TRANSITIONS: dict[DocState, set[DocState]] = {
    DocState.UPLOADED:   {DocState.PARSING, DocState.FAILED, DocState.DELETED},
    DocState.PARSING:    {DocState.PARSED, DocState.FAILED},
    DocState.PARSED:     {DocState.CHUNKING, DocState.FAILED, DocState.REINDEXING},
    DocState.CHUNKING:   {DocState.EMBEDDING, DocState.FAILED},
    DocState.EMBEDDING:  {DocState.INDEXING, DocState.FAILED},
    DocState.INDEXING:   {DocState.READY, DocState.FAILED},
    DocState.READY:      {DocState.REINDEXING, DocState.FAILED, DocState.DELETED},
    DocState.FAILED:     {DocState.PARSING, DocState.REINDEXING, DocState.DELETED},
    DocState.DELETED:    set(),  # Terminal
    DocState.REINDEXING: {DocState.PARSING, DocState.READY, DocState.FAILED},
}


class DocStateMachine:
    """文档状态机 — 带日志记录"""

    @staticmethod
    def transition(
        doc,
        new_state: str,
        reason: Optional[str] = None,
    ) -> bool:
        """执行状态转换，返回是否成功"""
        current = DocState(doc.status) if doc.status in DocState.__members__ else DocState.UPLOADED
        target = DocState(new_state)

        if target not in TRANSITIONS.get(current, set()):
            logger.error(
                f"Invalid state transition: {current.value} → {target.value} "
                f"(doc={doc.id}, reason={reason})"
            )
            return False

        old = current.value
        doc.status = target.value
        logger.info(
            f"State transition: {old} → {target.value} "
            f"(doc={doc.id}, reason={reason or 'N/A'})"
        )
        return True

    @staticmethod
    def can_transition(current: str, target: str) -> bool:
        cs = DocState(current) if current in DocState.__members__ else DocState.UPLOADED
        ts = DocState(target)
        return ts in TRANSITIONS.get(cs, set())

    @staticmethod
    def valid_transitions(current: str) -> list[str]:
        cs = DocState(current) if current in DocState.__members__ else DocState.UPLOADED
        return [t.value for t in TRANSITIONS.get(cs, set())]


class JobState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    RETRYING = "RETRYING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
