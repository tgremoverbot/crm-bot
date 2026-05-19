from __future__ import annotations

import enum


class MaterialKind(str, enum.Enum):
    TEXT = "text"
    PHOTO = "photo"
    DOCUMENT = "document"
    VIDEO = "video"
    LINK = "link"


class ParseMode(str, enum.Enum):
    MARKDOWN_V2 = "MarkdownV2"
    HTML = "HTML"
    NONE = "none"


class SequenceTriggerKind(str, enum.Enum):
    CAMPAIGN_JOIN = "campaign_join"
    MANUAL = "manual"
    TAG_ADDED = "tag_added"


class ScheduledMessageStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    FAILED_TERMINAL = "failed_terminal"
    CANCELLED = "cancelled"


class SourceKind(str, enum.Enum):
    SEQUENCE = "sequence"
    BROADCAST = "broadcast"
    MANUAL = "manual"
