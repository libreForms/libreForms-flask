FROM python:3.8
RUN mkdir /libreForms/
COPY .. /libreForms/
WORKDIR /libreForms/
RUN mv etc/config_overrides.py.example app/config_overrides.py
EXPOSE 8000
RUN pip install -r requirements/app.txt
