FROM python:3.6
ADD ./part1/src /part1/src
WORKDIR /
RUN pip3 install -r /part1/src/requirements.txt
CMD python3 /part1/src/app.py
