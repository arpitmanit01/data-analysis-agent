FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application.
COPY src ./src
COPY app ./app
COPY tests ./tests

EXPOSE 8501

# Default: launch the Streamlit UI. Override the command to use the CLI, e.g.
#   docker run --rm --env-file .env <image> \
#     python src/agent.py --csv tests/data/sales.csv --query "..."
CMD ["streamlit", "run", "app/streamlit_app.py", \
     "--server.address=0.0.0.0", "--server.port=8501"]
