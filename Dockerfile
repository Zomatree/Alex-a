FROM python:3.9.5-buster

ENV LANG C.UTF-8
ENV TZ=etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY ./bot-requirements.txt /

RUN python3.9 -m pip install -r bot-requirements.txt && apt-get update && apt-get install libopus0

WORKDIR /bot

# running in unbuffered mode because print isnt working half the time :rolling_eyes:

CMD ["python3.9", "-u", "bot.py"]
