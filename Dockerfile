# AlmaLinux 9をベースイメージとして使用
FROM almalinux:9

# メタデータを設定
LABEL maintainer="Mirai AI Team"
LABEL description="Mirai AI Server with Ollama and LLaMA 2"

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージを更新し、Python3とpipをインストール
# SQLite 3.35.0以上が必要（ChromaDB用）
RUN dnf update -y && \
    dnf install -y python3 python3-pip python3-devel gcc curl git wget make tcl zlib-devel --allowerasing && \
    dnf clean all

# SQLiteを最新版にアップグレード（ソースからビルド）
# ChromaDBはSQLite 3.35.0以上を要求
# 2024年12月時点の最新安定版を使用
RUN cd /tmp && \
    SQLITE_VERSION=3450300 && \
    wget https://www.sqlite.org/2024/sqlite-autoconf-${SQLITE_VERSION}.tar.gz && \
    tar xzf sqlite-autoconf-${SQLITE_VERSION}.tar.gz && \
    cd sqlite-autoconf-${SQLITE_VERSION} && \
    ./configure --prefix=/usr/local --enable-fts5 && \
    make -j$(nproc) && \
    make install && \
    cd / && \
    rm -rf /tmp/sqlite-autoconf-${SQLITE_VERSION}* && \
    echo "/usr/local/lib" > /etc/ld.so.conf.d/sqlite.conf && \
    ldconfig

# Pythonのシンボリックリンクを作成（pythonコマンドでpython3を実行）
RUN ln -sf /usr/bin/python3 /usr/bin/python

# pipを最新版にアップグレード
RUN python -m pip install --upgrade pip

# アプリケーションの依存関係をコピー
COPY requirements.txt .

# Pythonの依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのソースコードをコピー
COPY . .

# スクリプトに実行権限を付与
RUN chmod +x scripts/*.py

# ヘルスチェックを追加
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# デフォルトコマンド（FastAPIアプリケーションを起動）
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

