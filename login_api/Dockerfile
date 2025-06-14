FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install flask requests
RUN pip install python-dotenv
CMD ["python", "app.py"]
