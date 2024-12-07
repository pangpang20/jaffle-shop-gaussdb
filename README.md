# The Jaffle Shop For GaussDB and DWS

这个DEMO项目将展示如何使用dbt-core和dbt-gaussdbdws插件来开发一个数据仓库项目。支持华为GaussDB和DWS。


##  前提条件

- 华为云GaussDB或DWS的账号密码及其连接信息。
- 具备linux基本操作能力。
- 具备dbt-core的基本使用能力。

## 安装插件
克隆项目到本地
在项目根目录下执行以下命令安装插件
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m pip install dbt-core dbt-gaussdbdws
```
如果安装报错提示http2协议错误，请使用以下命令：
```bash
git config --global http.version HTTP/1.1
```

查看版本信息
```bash
dbt --version
pip show dbt-core dbt-gaussdbdws

```

更新插件
```bash
pip install --upgrade dbt-gaussdbdws
```

## 配置项目
### 创建数据库和用户
GaussDB中创建用户和数据库，参考SQL：
```sql
CREATE USER dbt_user WITH PASSWORD 'Dbtuser@123';
GRANT ALL PRIVILEGES to dbt_user;
CREATE DATABASE dbt_test OWNER = "dbt_user" TEMPLATE = "template0" ENCODING = 'UTF8'   CONNECTION LIMIT = -1;
```


### 修改profiles.yml
```bash
cp sample-profiles.yml profiles.yml
vi profiles.yml
jaffle_shop:
  target: dev_gaussdb
  outputs:
    dev_gaussdb:
      type: gaussdbdws
      host: xx.xx.xx.xx
      user: dbt_user
      password: Dbtuser@123
      port: 8000
      dbname: dbt_test
      schema: jaffle-shop
      threads: 4

```

### 修改dbt_project.yml
修改dbt_project.yml中的profile，schema为 profiles.yml中的值：
```bash
profile: jaffle_shop
+schema: jaffle_shop
```
DEMO中已经配置好了，如果不一致，请参考上面修改。

参数`gaussdb_type` ,默认为0，主要区分是否有系统表`pg_matviews`,如果存在，设置为1。一般内核9.x的默认是没有这个系统表，需要设置为0。

### 测试连接
使用下面的命令测试连接
```bash
dbt debug
```
如果连接成功，会输出类似下面的信息：
```bash
... ...
03:28:45    profiles.yml file [OK found and valid]
03:28:45    dbt_project.yml file [OK found and valid]
03:28:45  Required dependencies:
03:28:45   - git [OK found]

03:28:45  Connection:
03:28:45    host: 123.249.121.53
03:28:45    port: 8000
03:28:45    user: dbt_user
03:28:45    database: dbt_test
03:28:45    schema: jaffle-shop
03:28:45    connect_timeout: 10
03:28:45    role: None
03:28:45    search_path: None
03:28:45    keepalives_idle: 0
03:28:45    sslmode: None
03:28:45    sslcert: None
03:28:45    sslkey: None
03:28:45    sslrootcert: None
03:28:45    application_name: dbt
03:28:45    retries: 3
03:28:45  Registered adapter: gaussdbdws=1.0.1
03:28:45    Connection test: [OK connection ok]

03:28:45  All checks passed!
```

如果输出下面的信息，说明GaussDB的参数`password_encryption_type`为2，用户密码加密默认保存方式为SHA256，需要修改为1，同时支持MD5和SHA256的兼容模式。
```bash

connection to server at "xx.xx.xx.xx", port 8000 failed: none of the server's SASL authentication mechanisms are supported
```
原因是原生的psycopg2不支持SHA256的加密方式，只支持MD5。
下面提供两个途径实现修改：
- 联系GaussDB技术支持，修改参数`password_encryption_type`为1。
- 参考下面的方法，使用GaussDB提供的psycopg2替换原生psycopg2。
  ```bash
    # 华为云官网获取驱动包
    wget -O /tmp/GaussDB_driver.zip https://dbs-download.obs.cn-north-1.myhuaweicloud.com/GaussDB/1730887196055/GaussDB_driver.zip

    # 解压下载的文件
    unzip /tmp/GaussDB_driver.zip -d /tmp/ && rm /tmp/GaussDB_driver.zip

    # 复制驱动到临时目录
    \cp /tmp/GaussDB_driver/Centralized/Hce2_arm_64/GaussDB-Kernel_505.2.0_Hce_64bit_Python.tar.gz /tmp/

    # 解压版本对应驱动包
    tar -zxvf /tmp/GaussDB-Kernel_505.2.0_Hce_64bit_Python.tar.gz -C /tmp/ && rm /tmp/GaussDB-Kernel_505.2.0_Hce_64bit_Python.tar.gz

    # 卸载原生psycopg2
    pip uninstall -y $(pip list | grep psycopg2 | awk '{print $1}')


    # 将 psycopg2 复制到 python 安装目录下的 site-packages 文件夹下
    \cp /tmp/psycopg2 $(python3 -c 'import site; print(site.getsitepackages()[0])') -r

    # 修改 psycopg2 目录权限为 755
    chmod 755 $(python3 -c 'import site; print(site.getsitepackages()[0])')/psycopg2 -R

    # 将 psycopg2 目录添加到环境变量 $PYTHONPATH，并使之生效
    echo 'export PYTHONPATH="${PYTHONPATH}:$(python3 -c '\''import site; print(site.getsitepackages()[0])'\'')"' >> .venv/bin/activate

    # 对于非数据库用户，需要将解压后的 lib 目录，配置在 LD_LIBRARY_PATH 中
    echo 'export LD_LIBRARY_PATH="/tmp/lib:$LD_LIBRARY_PATH"' >> .venv/bin/activate

    # 激活虚拟环境,使之生效
    source .venv/bin/activate

    # 测试是否可以使用 psycopg2,没有报错即可
    (.venv) [root@ecs-euleros-dev ~]# python3
    Python 3.9.9 (main, Jun 19 2024, 02:50:21)
    [GCC 10.3.1] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import psycopg2
    >>> exit()
  ```


### 加载数据


```yaml dbt_project.yml
seed-paths: ["seeds", "jaffle-data"]
```

```bash
dbt seed
```

## 启动项目

执行 `dbt build` 来运行项目

### 检查数据
