#!/usr/bin/env bash

# Hatalarda hemen çıkış yap
set -o errexit

# Python sanal ortamını oluştur veya etkinleştir.
# Eğer .venv klasörü varsa silip yeniden oluşturmak, temiz bir başlangıç sağlar.
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate

# pip'i güncel tut
pip install --upgrade pip

# requirements.txt dosyasındaki tüm bağımlılıkları yükle
pip install -r requirements.txt

# Uvicorn ve FastAPI'yi de ayrıca yükle (zaten requirements.txt'de olmalı,
# ancak emin olmak için buraya da ekleyebiliriz, zararı olmaz).
# [standard] özelliği, uvicorn'ın gerekli diğer alt bağımlılıklarını da yüklemesini sağlar.
pip install "uvicorn[standard]"
pip install fastapi
