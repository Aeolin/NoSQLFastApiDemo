from datetime import datetime
from typing import Optional, Annotated

from bson import ObjectId
from fastapi.exceptions import HTTPException
import requests
import socket
import fastapi
from fastapi import Body
import uvicorn
from pydantic import Field, BaseModel, AfterValidator, BeforeValidator
import pymongo

mongo_client = pymongo.AsyncMongoClient("mongodb://localhost:27017/")
db = mongo_client["fastapi_db"]

app = fastapi.FastAPI()

def objectid_to_str(value) -> str:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, str) and ObjectId.is_valid(value):
        return value
    raise ValueError("Invalid ObjectId")

PyObjectId = Annotated[str, BeforeValidator(objectid_to_str)]

class SayHelloRequestModel(BaseModel):
    first_name: str
    last_name: str
    age: int = Field(..., strict=False, ge=18)

class EntityBase(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

class SayHelloModel(EntityBase):
    first_name: str
    last_name: str
    age: int
    timestamp: datetime

class SayHelloResponseModel(BaseModel):
    name: str
    timestamp: datetime

@app.post("/api/v1/say-hello")
async def say_hello(data: SayHelloRequestModel = Body(...)):
    collection = db.get_collection("say_hello")
    data_dump = data.model_dump()
    db_model = SayHelloModel(**data_dump, timestamp=datetime.now())
    db_model_dump = db_model.model_dump(exclude=["id"])
    result = await collection.insert_one(db_model_dump)
    return {"message": f"Hello, {data.first_name} {data.last_name}"}

def say_hello_to_response(item: dict) -> SayHelloResponseModel:
    return SayHelloResponseModel(
        name=f"{item['first_name']} {item['last_name']}",
        timestamp=item["timestamp"]
    )

@app.get("/api/v1/say-hello")
async def get_say_hello(min_date: Optional[datetime] = None) -> list[SayHelloResponseModel]:
    collection = db.get_collection("say_hello")
    find = collection.find() if min_date is None else collection.find({"timestamp": {"$gte": min_date}})
    result = await find.to_list(1000)
    models = [say_hello_to_response(item) for item in result]
    return models

@app.post("/api/v1/ping")
async def ping(data: dict = Body(...)):
    return {"message": "pong", "data": data}

@app.get("/api/v1/ping")
def get_ping() -> dict:
    return {"message": "pong"}

# run app
if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)
