from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from src.dal import ToDoDAL, ListSummary, ToDoList

COLLECTION_NAME = "todo_lists"

# ⚠️ Use environment variable (Render → Environment)
MONGODB_URI = os.environ.get("MONGODB_URI")

DEBUG = os.environ.get("DEBUG", "").strip().lower() in {"1", "true", "on", "yes"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not MONGODB_URI:
        raise Exception("MONGODB_URI not set!")

    client = AsyncIOMotorClient(MONGODB_URI)
    database = client.get_default_database()

    # ✅ Check connection
    pong = await database.command("ping")
    if int(pong["ok"]) != 1:
        raise Exception("MongoDB connection failed!")

    app.todo_dal = ToDoDAL(database.get_collection(COLLECTION_NAME))

    yield

    client.close()

app = FastAPI(lifespan=lifespan, debug=DEBUG)

# ✅ CORS (Allow your frontend later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change later for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- MODELS ----------
class NewList(BaseModel):
    name: str

class NewItem(BaseModel):
    label: str

class ListItemCheckedState(BaseModel):
    item_id: str
    checked_state: bool

# ---------- ROUTES ----------
@app.get("/api/lists")
async def get_all_lists() -> list[ListSummary]:
    return [i async for i in app.todo_dal.list_todo_lists()]

@app.post("/api/lists", status_code=status.HTTP_201_CREATED)
async def create_todo_list(new_list: NewList) -> str:
    return await app.todo_dal.create_todo_list(new_list.name)

@app.get("/api/lists/{list_id}")
async def get_list(list_id: str) -> ToDoList:
    return await app.todo_dal.get_todo_list(list_id)

@app.delete("/api/lists/{list_id}")
async def delete_list(list_id: str) -> bool:
    return await app.todo_dal.delete_todo_list(list_id)

@app.post("/api/lists/{list_id}/items", status_code=status.HTTP_201_CREATED)
async def create_item(list_id: str, new_item: NewItem) -> ToDoList:
    return await app.todo_dal.create_item(list_id, new_item.label)

@app.patch("/api/lists/{list_id}/checked_state")
async def set_checked_state(list_id: str, update: ListItemCheckedState) -> ToDoList:
    return await app.todo_dal.set_checked_state(
        list_id, update.item_id, update.checked_state
    )

@app.delete("/api/lists/{list_id}/items/{item_id}")
async def delete_item(list_id: str, item_id: str) -> ToDoList:
    return await app.todo_dal.delete_item(list_id, item_id)