# Gunakan image python 3.11 bookworm (full) yang jauh lebih stabil daripada versi slim/testing
FROM python:3.11-bookworm

# Set environment variabel agar Python output tidak di-buffer
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Tentukan work directory di dalam docker
WORKDIR /app

# Install system dependencies yang diperlukan untuk OpenCV/YOLO
# Versi Bookworm (Stable) memiliki mirror yang jauh lebih handal
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy dependency list dan install
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy sisa folder lokal ke image
COPY . /app/

# Mengekspose port aplikasi (5000)
EXPOSE 5000

# Jalankan webserver production gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
