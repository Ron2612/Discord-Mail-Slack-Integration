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


@app.post("/email/link")
async def sending_link_with_message(
    subject: str = Form(...),
    link: str = Form(...),
    body: str = Form(...),
    email: UploadFile = File(...),
) -> JSONResponse:
    message_subject = subject
    link = markdown.markdown(link)
    link = re.compile(r'<.*?>').sub('', link)
    message_body = link + "\n" + body

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
        return JSONResponse(status_code=200, content={"message": "email has been sent"})


@app.post("/email/schedulingMessage")
async def scheduling(
        subject: str = Form(...),
        body: str = Form(...),
        email: UploadFile = File(...),
        date_and_time: str = Form(...)
) -> JSONResponse:

    year = date_and_time[:4]
    month = date_and_time[5:7]
    day = date_and_time[8:10]
    hour = date_and_time[11:13]
    minute = date_and_time[14:16]

    if datetime.datetime.now() > datetime.datetime(year=int(year), month=int(month), day=int(day), hour=int(hour), minute=int(minute)):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content='Past is out of your hands')

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

    async def scheduling_message_schema():
        message = MessageSchema(
            recipients=[mails for mails in dataframe[0]],
            subject=subject,
            body=body,
            subtype="text"
        )

        try:
            fm = FastMail(conf)
            return await fm.send_message(message)

        except Exception as e:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    try:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(scheduling_message_schema, 'cron', year=year, month=month, day=day, hour=hour, minute=minute,
                          second='00', timezone="Asia/Kolkata")
        scheduler.start()
        print(scheduler.get_jobs())

    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content="Mail scheduled Successfully")


@app.post("/email/schedulingLink")
async def scheduling_link(
        subject: str = Form(...),
        body: str = Form(...),
        link: str = Form(...),
        email: UploadFile = File(...),
        date_and_time: str = Form(...)
) -> JSONResponse:
    year = date_and_time[:4]
    month = date_and_time[5:7]
    day = date_and_time[8:10]
    hour = date_and_time[11:13]
    minute = date_and_time[14:16]

    if datetime.datetime.now() > datetime.datetime(year=int(year), month=int(month), day=int(day), hour=int(hour), minute=int(minute)):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content='Past is out of your hands')

    link = markdown.markdown(link)
    link = re.compile(r'<.*?>').sub('', link)

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

    async def scheduling_message_schema():
        message = MessageSchema(
            recipients=[mails for mails in dataframe[0]],
            subject=subject,
            body=link + "\n" + body,
            subtype="text"
        )
        try:
            fm = FastMail(conf)
            return await fm.send_message(message)

        except Exception as e:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    try:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(scheduling_message_schema, 'cron', year=year, month=month, day=day, hour=hour, minute=minute,
                          second='00', timezone="Asia/Kolkata")
        scheduler.start()
        print(scheduler.get_jobs())

    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content="Mail scheduled Successfully")


client = discord.Client()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(client.start('DISCORD_BOT_TOKEN'))


@app.post("/discord/message")
async def sending_message(message: str):
    channel_id = 955391175823618072
    channel = client.get_channel(channel_id)
    try:
        await channel.send(message)

    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content='Message sent Successfully.')


@app.post("/discord/file_with_message")
async def sending_message_and_file(message: str = Form(...), file: UploadFile = Form(...)):
    channel_id = 955391175823618072
    channel = client.get_channel(channel_id)

    try:
        try:
            suffix = Path(file.filename).suffix
            with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = Path(tmp.name)
        finally:
            file.file.close()

        await channel.send(content=message, tts=False, embed=None,
                           file=discord.File(tmp_path, spoiler=True), files=None, delete_after=None, nonce=None,
                           allowed_mentions=None, reference=None, mention_author=None)

    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content='File and Message sent Successfully.')

    finally:
        os.remove(tmp_path)


@app.post("/discord/link_with_message")
async def sending_message_and_link(message: str, link: str):
    channel_id = 955391175823618072
    channel = client.get_channel(channel_id)

    link = markdown.markdown(link)
    link = re.compile(r'<.*?>').sub('', link)
    try:
        await channel.send(message + "\n" + link)

    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content='Message sent Successfully.')


@app.post("/discord/schedule_message")
async def scheduling_message(message: str, date_and_time: str):
    year = date_and_time[:4]
    month = date_and_time[5:7]
    day = date_and_time[8:10]
    hour = date_and_time[11:13]
    minute = date_and_time[14:16]

    if datetime.datetime.now() > datetime.datetime(year=int(year), month=int(month), day=int(day), hour=int(hour), minute=int(minute)):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content='Past is out of your hands')

    async def scheduling_message_send():
        channel_id = 955391175823618072
        channel = client.get_channel(channel_id)
        try:
            return await channel.send(message)

        except Exception as e:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    try:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(scheduling_message_send, 'cron', year=year, month=month, day=day, hour=hour, minute=minute,
                          second='00', timezone="Asia/Kolkata")

        scheduler.start()
        print(scheduler.get_jobs())

    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content='Message Scheduled Successfully')


@app.post("/discord/schedule_link_with_message")
async def scheduling_message_and_link(message: str, date_and_time: str, link: str,):
    link = markdown.markdown(link)
    link = re.compile(r'<.*?>').sub('', link)

    year = date_and_time[:4]
    month = date_and_time[5:7]
    day = date_and_time[8:10]
    hour = date_and_time[11:13]
    minute = date_and_time[14:16]

    if datetime.datetime.now() > datetime.datetime(year=int(year), month=int(month), day=int(day), hour=int(hour), minute=int(minute)):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content='Past is out of your hands')

    async def scheduling_message_send():
        channel_id = 955391175823618072
        channel = client.get_channel(channel_id)
        try:
            return await channel.send(message + "\n" + link)

        except Exception as e:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    try:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(scheduling_message_send, 'cron', year=year, month=month, day=day, hour=hour, minute=minute,
                          second='00', timezone="Asia/Kolkata")

        scheduler.start()
        print(scheduler.get_jobs())

    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content='Message Scheduled Successfully')


@app.post("/slack/message")
async def sending_message(message: str):
    slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
    logger = logging.getLogger(__name__)

    channel_id = "C03826TDBTL"

    try:
        result = slack_client.chat_postMessage(
            channel=channel_id,
            text=message
        )

        logger.info(result)

    except SlackApiError as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content='Message Sent Successfully')


@app.post("/slack/file_with_message")
async def sending_message_and_file(message: str = Form(...), file: UploadFile = File(...)):
    slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
    logger = logging.getLogger(__name__)

    try:
        suffix = Path(file.filename).suffix
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = str(Path(tmp.name))

    finally:
        file.file.close()

    channel_id = "C037MJK184F"

    try:
        result = slack_client.files_upload(
            channels=channel_id,
            initial_comment=message,
            file=tmp_path
        )

        logger.info(result)

    except SlackApiError as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content='Message Sent Successfully')

    finally:
        os.remove(tmp_path)


@app.post("/slack/link_with_message")
async def sending_message_and_link(message: str, link: str):
    slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
    logger = logging.getLogger(__name__)

    channel_id = "C039T5WBGG0"

    link = markdown.markdown(link)
    link = re.compile(r'<.*?>').sub('', link)

    try:
        result = slack_client.chat_postMessage(
            channel=channel_id,
            text=message + "\n" + link
        )

        logger.info(result)

    except SlackApiError as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content='Message sent Successfully')


@app.post("/slack/schedule_message")
async def scheduling_message(message: str, date_and_time: str):
    slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
    logger = logging.getLogger(__name__)

    year = date_and_time[:4]
    month = date_and_time[5:7]
    day = date_and_time[8:10]
    hour = date_and_time[11:13]
    minute = date_and_time[14:16]

    date_and_time = datetime.datetime.strptime(date_and_time, '%Y-%m-%d %H:%M')

    channel_id = "C038RVCR19N"

    if datetime.datetime.now() > datetime.datetime(year=int(year), month=int(month), day=int(day), hour=int(hour), minute=int(minute)):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content='Past is out of your hands')


    try:
        result = slack_client.chat_scheduleMessage(
            channel=channel_id,
            text=message,
            post_at=int(date_and_time.timestamp())
        )

        logger.info(result)

    except SlackApiError as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content='Message scheduled Successfully')


@app.post("/slack/schedule_link_with_message")
async def scheduling_message_and_link(message: str, link: str, date_and_time: str):
    slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
    logger = logging.getLogger(__name__)

    year = date_and_time[:4]
    month = date_and_time[5:7]
    day = date_and_time[8:10]
    hour = date_and_time[11:13]
    minute = date_and_time[14:16]

    date_and_time = datetime.datetime.strptime(date_and_time, '%Y-%m-%d %H:%M')
    print(type(date_and_time))

    channel_id = "C0390GC1F6Z"

    if datetime.datetime.now() > datetime.datetime(year=int(year), month=int(month), day=int(day), hour=int(hour), minute=int(minute)):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content='Past is out of your hands')

    link = markdown.markdown(link)
    link = re.compile(r'<.*?>').sub('', link)
    try:
        result = slack_client.chat_scheduleMessage(
            channel=channel_id,
            text=message + '\n' + link,
            post_at=int(date_and_time.timestamp())
        )
        # Log the result
        logger.info(result)

    except SlackApiError as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e)

    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content='Message scheduled Successfully')
