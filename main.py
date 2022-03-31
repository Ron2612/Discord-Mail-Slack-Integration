import os

from fastapi import (
    FastAPI,
    BackgroundTasks,
    UploadFile, File, Form
)
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from typing import List
from starlette import status
from starlette.responses import JSONResponse
import shutil
from tempfile import NamedTemporaryFile
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import markdown
import re
import datetime
import asyncio


from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import pandas as pd
import pandas.errors


import discord


from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("EMAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("EMAIL_PASSWORD"),
    MAIL_FROM=os.getenv("EMAIL_ID"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_TLS=True,
    MAIL_SSL=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)


@app.post("/email")
async def sending_message(
    subject: str = Form(...),
    body: str = Form(...),
    email: UploadFile = File(...),
) -> JSONResponse:
    message_subject = subject
    message_body = body

    try:
        dataframe = pd.read_csv(email.file, index_col=False, delimiter=',', header=None)

    except pandas.errors.EmptyDataError:
        print("Provided csv file is empty")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={'message': 'Provided csv file is empty.'})

    if not email.filename.endswith('.csv'):
        print("Please provide a csv file only")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={'message': 'Please provide a csv file only.'})

    message = MessageSchema(
        recipients=[mails for mails in dataframe[0]],
        subject=message_subject,
        body=message_body,
        subtype="text"
    )

    try:
        fm = FastMail(conf)
        await fm.send_message(message)

    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "email has been sent"})


@app.post("/email/file_with_message")
async def sending_message_and_file(
        background_tasks: BackgroundTasks,
        subject: str = Form(...),
        body: str = Form(...),
        email: UploadFile = File(...),
        file: List[UploadFile] = Form(...)
) -> JSONResponse:

    try:
        dataframe = pd.read_csv(email.file, index_col=False, delimiter=',', header=None)

    except pandas.errors.EmptyDataError:
        print("Provided csv file is empty")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={'message': 'Provided csv file is empty.'})

    if not email.filename.endswith('.csv'):
        print("Please provide a csv file only")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={'message': 'Please provide a csv file only.'})

    message = MessageSchema(
        recipients=[mails for mails in dataframe[0]],
        subject=subject,
        body=body,
        subtype="text",
        attachments=file
    )

    try:
        fm = FastMail(conf)
        background_tasks.add_task(fm.send_message, message)

    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    else:
        return JSONResponse(status_code=200, content={"message": "email has been sent"})
