from pydantic import BaseModel
from typing import Optional
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from typing import Union
from datetime import datetime


class DockerContainerStats(BaseModel):
    id: str
    state: str
    name: str
    memory_usage: int
    hostname: Optional[str]
    node: str
    created: str
    
class DockerContainerStatsRepository:
    def __init__(self, client: MongoClient):
        self.db = client['docker']
        self.collection = self.db['container_stats']
        
        self.collection.create_index("name", unique=True)
        self.collection.create_index("id", unique=True)
        

    def add(self, record: Union[dict, DockerContainerStats]):
        
        if not isinstance(record, dict):
            record = record.model_dump()

        record['created'] = datetime.now().isoformat()
        
        try:
            self.collection.insert_one(record)
        except (DuplicateKeyError, ValueError):
            record.pop('_id', None)
            self.collection.update_one(
                {"id": record["id"]},
                {"$set": record}
            )

    def find_by_name(self, name: str) -> Optional[DockerContainerStats]:
        result = self.collection.find_one({"name": name})
        if result:
            return DockerContainerStats(**result)
        return None

    def find_by_id(self, id: str) -> Optional[DockerContainerStats]:
        result = self.collection.find_one({"id": id})
        if result:
            return DockerContainerStats(**result)
        return None
    
    @property
    def all(self):
        return [DockerContainerStats(**r) for r in self.collection.find()]
    
    def delete(self, id: str):
        self.collection.delete_one({"id": id})