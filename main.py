import logging
from datetime import datetime, timedelta
from typing import Annotated

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext
from pydantic import ValidationError
from sqlalchemy.orm import Session

from db import crud, models
from db.database import SessionLocal, Base, engine
from schemas import user, message

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

logging.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s',
                    level=logging.DEBUG)

Base.metadata.create_all(bind=engine)

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_db():
    """
    Dependency function yielding a global Session object used by all endpoints to communicate
    with the local database.

    Will close the session connection after each use.

    :return: An instance of SQLAlchemys' Session object.
    """

    db = SessionLocal()

    try:
        yield db
    except ValidationError as err:
        logging.error(err)
    finally:
        db.close()


def create_access_token(data: dict,
                        expires_delta: timedelta | None = None) -> str:
    """
    Creates and returns a JWT.

    :param data: The 'sub' and expiration date/time of the JWT.
    :param expires_delta: Time between now and the JWT expiration.
    :return: The string of the newly generated JWT.
    """

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def validate_password(password: str, hashed_password: bytes) -> bool:
    """
    Validates the provided user password.

    :param password: A user password string.
    :param hashed_password: The hashed password stored in the database.
    :return: True if the JWT is valid False if not.
    """
    return pwd_context.verify(bytes(password, "utf-8"), hashed_password)


async def validate_token(token: Annotated[str, Depends(oauth2_scheme)],
                         db: Session = Depends(get_db)) -> models.User:
    """
    Validates the coding and expiration date of a give JWT.

    :param token: The JWT to validate.
    :param db: A Session object used to communicate with the local database.
    :return: A models.User object for the username associated with the given JWT.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if username is None:
            raise credentials_exception

        db_user = await crud.get_user_by_name(db, username=username)

        if db_user is None:
            raise credentials_exception

        if db_user.logged_in is False:
            raise HTTPException(status_code=400, detail="User is not logged in.")

        return db_user
    except ExpiredSignatureError:
        username = jwt.decode(token,
                              SECRET_KEY,
                              algorithms=[ALGORITHM],
                              options={'verify_exp': False})["sub"]
        db_user = await crud.get_user_by_name(db, username=username)

        if db_user is None:
            raise credentials_exception

        await crud.logout_user(db, db_user)

        raise HTTPException(status_code=400, detail="JWT Expired.")
    except JWTError:
        raise credentials_exception


@app.post("/register", status_code=201)
async def create_user(request_user: user.RequestUser,
                db: Session = Depends(get_db)):
    """
    Register a new user in the local database.

    :param request_user: The username and password to register.
    :param db: A Session object used to communicate with the local database.
    :return: 201 if successfully registered the new user or 400 if failed to
        register the new user or the username already exists in the local database.
    """
    logging.info(f"Received new user registration.")
    logging.info(f"Checking to see if the username already exists in the database ...")

    db_user = await crud.get_user_by_name(db, username=request_user.username)

    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    request_user.password = pwd_context.hash(request_user.password)

    logging.info("Adding new user to database ...")
    await crud.create_user(db=db, request_user=request_user)

    logging.info("Successfully added new user to database.")

    return "Successfully added new user to database."


@app.post("/login")
async def login_user(request_user: user.RequestUser,
                     db: Session = Depends(get_db)):
    """
    Login the user and returns a JWT to be used for all requests made by this user.

    :param request_user: The username and password to login.
    :param db: A Session object used to communicate with the local database.
    :return: A new JWT for the given user.
    """
    db_user = await crud.get_user_by_name(db, request_user.username)

    if not db_user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    if validate_password(request_user.password, db_user.hashed_password) is False:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    if db_user.logged_in:
        return "User already logged in."

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": request_user.username},
                                       expires_delta=access_token_expires)

    await crud.login_user(db, db_user)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.get("/logout")
async def logout_user(token: str = Depends(oauth2_scheme),
                      db: Session = Depends(get_db)):
    """
    Log out the user associated with the given bearer token.

    :param token: The JWT to authenticate the user with.
    :param db: A Session object used to communicate with the local database.
    :return: 200 If successfully logged out the user.
    """
    db_user = await validate_token(token, db)

    await crud.logout_user(db, db_user)

    return "User logout successful."


@app.get("/messages")
async def get_all_messages(token: str = Depends(oauth2_scheme),
                           db: Session = Depends(get_db)):
    """
    Returns all messages in the local database.

    :param token: The JWT to authenticate the user with.
    :param db: A Session object used to communicate with the local database.
    :return: A list of all messages stored in the local database.
    """
    await validate_token(token, db)

    all_messages = await crud.get_all_messages(db)

    return all_messages


@app.post("/messages", status_code=201)
async def post_message(new_message: message.MessageBase,
                       token: str = Depends(oauth2_scheme),
                       db: Session = Depends(get_db)):
    """
    Post a new message.

    :param new_message: The new message to post.
    :param token: The JWT to authenticate the user with.
    :param db: A Session object used to communicate with the local database.
    :return: A list of all messages stored in the local database.
    """
    db_user = await validate_token(token, db)

    await crud.post_message(db, new_message, db_user)

    return "Message posted successfully."


@app.post("/messages/{message_id}/vote", status_code=201)
async def vote_for_message(message_id: int,
                           vote: message.MessageVote,
                           token: str = Depends(oauth2_scheme),
                           db: Session = Depends(get_db)):
    """
    Vote for a message, can vote either 'up' or 'down'.

    :param message_id: The message ID to vote for.
    :param vote: Either 'up' or 'down'.
    :param token: The JWT to authenticate the user with.
    :param db: A Session object used to communicate with the local database.
    :return: 200 if the vote registered successfully.
    """
    await validate_token(token, db)

    db_message = await crud.get_message(db, message_id)

    if db_message is None:
        raise HTTPException(status_code=400, detail="Did not find message in database.")

    await crud.vote_for_message(db, db_message, vote.vote)

    return "Vote registered successfully."


@app.delete("/messages/{message_id}")
async def delete_message(message_id: int,
                         token: str = Depends(oauth2_scheme),
                         db: Session = Depends(get_db)):
    """
    Delete a message in the local database.

    :param message_id: The message ID to delete.
    :param token: The JWT to authenticate the user with.
    :param db: A Session object used to communicate with the local database.
    :return: 200 if the message was removed successfully.
    """
    await validate_token(token, db)

    db_message = await crud.get_message(db, message_id)

    if db_message is None:
        raise HTTPException(status_code=400, detail="Cannot find message ID.")

    await crud.delete_message(db, message_id)

    return "Message deleted successfully."


@app.get("/user/messages")
async def delete_message(token: str = Depends(oauth2_scheme),
                         db: Session = Depends(get_db)):
    """
    Returns all messages posted by the current user.

    :param token: The JWT to authenticate the user with.
    :param db: A Session object used to communicate with the local database.
    :return: 200 and a list of all messages posted by the given user.
    """
    db_user = await validate_token(token, db)

    user_messages = await crud.get_user_messages(db, db_user)

    if user_messages is None:
        raise HTTPException(status_code=200, detail="User has no messages.")

    return user_messages


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
