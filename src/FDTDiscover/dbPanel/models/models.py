from typing import Optional, TypedDict, List

from ....fdtdream.database import DatabaseHandler


class ParameterFetcherResult(TypedDict):
    simulationParameters: dict
    monitorParameters: dict
    token: str


class DBObject(TypedDict, total=False):
    type: str
    name: str
    dbHandler: DatabaseHandler
    id: Optional[id]


DBObjects = List[DBObject]
