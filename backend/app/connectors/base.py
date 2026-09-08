from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class NormalizedEvent:
    external_id: str
    title: str
    start_at: datetime
    end_at: datetime
    event_type: str | None = None
    campus: str | None = None
    building: str | None = None
    room: str | None = None
    teacher: str | None = None
    source_url: str | None = None
    source_updated_at: datetime | None = None


class ScheduleConnector(ABC):
    @abstractmethod
    async def search_courses(self, query: str): ...

    @abstractmethod
    async def get_course(self, external_id: str): ...

    @abstractmethod
    async def get_events(self, external_id: str) -> list[NormalizedEvent]: ...
