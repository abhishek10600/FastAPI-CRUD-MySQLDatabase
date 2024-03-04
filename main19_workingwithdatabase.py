from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
import random
from typing import List
from sqlalchemy import create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import uuid
from sqlalchemy import Column, String, DateTime, Integer
from datetime import datetime


## DATABSE ###

db_url = "mysql+pymysql://root:<password>@localhost:3306/fastapitest"

engine = create_engine(db_url)
sessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)

Base = declarative_base()


def get_db():  # this is a fuction to get the local instance of our db.
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()


try:
    with engine.connect() as connection:
        print("connected to database successfully.")
except Exception as e:
    print(f"Failed to connect to db. Reason {e}")

Base.metadata.create_all(bind=engine)

## Creating Tables in our database ##


class UserModel(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

### ------------------###


## Pydantic Schemas for the user request body ###

class User(BaseModel):
    name: str
    email: EmailStr


class UserIn(User):
    password: str


class UserResponse(User):
    id: str
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    total: int
    data: List[UserResponse]


class UserPatch(BaseModel):
    name: str | None = None
    email: EmailStr | None = None


### --------------------- ###


app = FastAPI()


@app.get("/")
def root():
    return {"message": "Welcome to fastapi"}


@app.get("/users", response_model=UserListResponse)
async def get_all_users(db: Session = Depends(get_db)):
    users = db.query(UserModel).all()
    return {"total": len(users), "data": users}


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user_detail(user_id: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    return user


@app.post("/users", response_model=UserResponse)
async def create_user(user: UserIn, db: Session = Depends(get_db)):
    new_user = UserModel(**user.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.patch("/users/{user_id}")
async def update_user(user_data: UserPatch, user_id: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if user_data.name:
        user.name = user_data.name
    if user_data.email:
        user.email = user_data.email
    db.commit()
    return user


@app.delete("/users/{user_id}")
async def delete_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return {"status": True, "message": "User deleted successfully."}
    raise HTTPException(status_code=404, detail="User not found.")
