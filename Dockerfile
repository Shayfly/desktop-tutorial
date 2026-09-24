FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN useradd --create-home --uid 10001 omni
COPY requirements-production.txt /app/requirements-production.txt
RUN python -m pip install --no-cache-dir -r /app/requirements-production.txt
COPY . /app
RUN chown -R omni:omni /app
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=3).read()"
CMD ["uvicorn","omni_prod.investor_app:app","--host","0.0.0.0","--port","8000","--proxy-headers","--forwarded-allow-ips=*"]
