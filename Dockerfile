# ১. Base Image: Jekhane Python ebong Playwright install kora ache
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# ২. Container-er bhetore working directory set kora
WORKDIR /app

# ৩. Requirements file copy kora ebong library install kora
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ৪. Playwright-er browser ebong tar dependencies install kora
RUN playwright install chromium
RUN playwright install-deps chromium

# ৫. Tomar folder-er shob file container-e copy kora
COPY . .

# ৬. Script-ti run korar command
CMD ["python", "main.py"]
