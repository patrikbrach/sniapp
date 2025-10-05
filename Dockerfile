FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sni_licenser_app_v12.py /app/

EXPOSE 8080
# Streamlit default port is 8501, but many hosts expect 8080; we set both env & args.
ENV PORT=8080

CMD ["bash", "-lc", "streamlit run sni_licenser_app_v12.py --server.port=${PORT:-8080} --server.address=0.0.0.0"]