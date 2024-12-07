FROM --platform=linux/arm64 ubuntu:22.04

WORKDIR /dbt_app

ENV DB_HOST=localhost \
    DB_PORT=8000 \
    DB_USER=dbt_user \
    DB_PASS=Dbtuser@123 \
    DB_NAME=dbt_test \
    DB_SCHEMA=jaffle_shop


ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    ca-certificates \
    wget \
    curl \
    gnupg \
    unzip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN echo "deb [arch=arm64] https://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/ jammy main restricted universe multiverse" > /etc/apt/sources.list && \
    echo "deb [arch=arm64] https://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/ jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb [arch=arm64] https://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/ jammy-security main restricted universe multiverse" >> /etc/apt/sources.list

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    python3 \
    python3-pip \
    python3-distutils \
    python3-venv \
    gettext \
    git \
    net-tools \
    iputils-ping \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY . /dbt_app/
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    python3 -m pip install --upgrade pip


RUN ln -s /usr/bin/python3 /usr/bin/python && \
    python3 -m venv /dbt_app/.venv

ENV PATH="/dbt_app/.venv/bin:$PATH"

RUN chmod +x /dbt_app/entrypoint.sh && \
    /dbt_app/.venv/bin/python3 -m pip install -r /dbt_app/requirements.txt && \
    /dbt_app/.venv/bin/python3 -m pip install dbt-core dbt-gaussdbdws && \
    dbt deps


RUN wget -O /tmp/GaussDB_driver.zip https://dbs-download.obs.cn-north-1.myhuaweicloud.com/GaussDB/1730887196055/GaussDB_driver.zip && \
    unzip /tmp/GaussDB_driver.zip -d /tmp/ && \
    rm -rf /tmp/GaussDB_driver.zip && \
    \cp /tmp/GaussDB_driver/Centralized/Hce2_arm_64/GaussDB-Kernel_505.2.0_Hce_64bit_Python.tar.gz /tmp/ && \
    tar -zxvf /tmp/GaussDB-Kernel_505.2.0_Hce_64bit_Python.tar.gz -C /tmp/ && \
    /dbt_app/.venv/bin/pip uninstall -y $(/dbt_app/.venv/bin/pip list | grep psycopg2 | awk '{print $1}') && \
    rm -rf /tmp/GaussDB-Kernel_505.2.0_Hce_64bit_Python.tar.gz && \
    rm -rf /tmp/GaussDB_driver && \
    \cp /tmp/psycopg2 $(/dbt_app/.venv/bin/python3 -c 'import site; print(site.getsitepackages()[0])') -r && \
    chmod 755 $(/dbt_app/.venv/bin/python3 -c 'import site; print(site.getsitepackages()[0])')/psycopg2 -R

ENV PYTHONPATH="${PYTHONPATH}:$(/dbt_app/.venv/bin/python3 -c 'import site; print(site.getsitepackages()[0])')"
ENV LD_LIBRARY_PATH="/tmp/lib:$LD_LIBRARY_PATH"

ENTRYPOINT ["/dbt_app/entrypoint.sh"]

CMD ["bash"]
