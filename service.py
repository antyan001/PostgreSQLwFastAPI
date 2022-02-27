#! /usr/bin/python3

from typing import List
import databases
import sqlalchemy
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import os
import urllib
import uvicorn

APP_PORT = 8002

#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
host_server = os.environ.get('host_server', 'localhost')
db_server_port = urllib.parse.quote_plus(str(os.environ.get('db_server_port', '5432')))
database_name = os.environ.get('database_name', 'etldb')
db_username = urllib.parse.quote_plus(str(os.environ.get('db_username', 'anthony')))
db_password = urllib.parse.quote_plus(str(os.environ.get('db_password', 'lolkek123')))
ssl_mode = urllib.parse.quote_plus(str(os.environ.get('ssl_mode', 'prefer')))

DATABASE_URL = 'postgresql://{}:{}@{}:{}/{}?sslmode={}'.format(db_username,
                                                               db_password,
                                                               host_server,
                                                               db_server_port,
                                                               database_name,
                                                               ssl_mode)
#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

database = databases.Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()

dbtbl = sqlalchemy.Table(
                            "sample_us_users",
                            metadata,
                            sqlalchemy.Column("id", sqlalchemy.String),
                            sqlalchemy.Column("address", sqlalchemy.String),
                            sqlalchemy.Column("inserted_at", sqlalchemy.DateTime),
                        )

engine = sqlalchemy.create_engine(
    DATABASE_URL, pool_size=5, max_overflow=0
)
metadata.create_all(engine)

# class NoteIn(BaseModel):
#     text: str
#     completed: bool

class Note(BaseModel):
    id: str
    address: str
    inserted_at: pd.Timestamp

app = FastAPI(title = "REST API using FastAPI PostgreSQL Async EndPoints")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.get("/sample_us_users/", response_model=List[Note], status_code = status.HTTP_200_OK)
async def read_notes(skip: int = 0, take: int = 20):
    query = dbtbl.select().offset(skip).limit(take)
    return await database.fetch_all(query)

@app.get("/sample_us_users/{note_id}/", response_model=Note, status_code = status.HTTP_200_OK)
async def read_notes(note_id: str):
    query = dbtbl.select().where(dbtbl.c.id == note_id)
    return await database.fetch_one(query)

# @app.post("/notes/", response_model=Note, status_code = status.HTTP_201_CREATED)
# async def create_note(note: NoteIn):
#     query = dbtbl.insert().values(text=note.text, completed=note.completed)
#     last_record_id = await database.execute(query)
#     return {**note.dict(), "id": last_record_id}

# @app.put("/notes/{note_id}/", response_model=Note, status_code = status.HTTP_200_OK)
# async def update_note(note_id: int, payload: NoteIn):
#     query = dbtbl.update().where(notes.c.id == note_id).values(text=payload.text, completed=payload.completed)
#     await database.execute(query)
#     return {**payload.dict(), "id": note_id}

@app.delete("/notes/{note_id}/", status_code = status.HTTP_200_OK)
async def delete_note(note_id: int):
    query = dbtbl.delete().where(dbtbl.c.id == note_id)
    await database.execute(query)
    return {"message": "Note with id: {} deleted successfully!".format(note_id)}


#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
def run_app():
    uvicorn.run("service:app", host="0.0.0.0", port=int(APP_PORT), reload=True, debug=True)
    # app.run(host="0.0.0.0", port=APP_PORT, debug=False, threaded=True, use_reloader=False)
#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

if __name__ == '__main__':
    run_app()