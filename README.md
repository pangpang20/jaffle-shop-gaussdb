# The Jaffle Shop For GaussDB

这个DEMO项目将展示如何使用dbt-core和dbt-gaussdbdws插件来开发一个数据仓库项目。支持华为GaussDB。


##  前提条件

- 华为云GaussDB或DWS的账号密码及其连接信息。
- 具备linux基本操作能力。
- 具备dbt-core的基本使用能力。

## 部署项目
提供两种方式部署项目：

- 克隆项目到本地，然后安装插件使用
- 使用docker部署，在容器中运行项目，好处是无需安装插件，直接运行即可


## 克隆项目到本地运行项目
### 安装插件
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

更新插件（可选）
```bash
pip install --upgrade dbt-gaussdbdws
```

### 配置项目
#### 创建数据库和用户
GaussDB中创建用户和数据库，参考SQL：
```sql
CREATE USER dbt_user WITH PASSWORD 'Dbtuser@123';
GRANT ALL PRIVILEGES to dbt_user;
CREATE DATABASE dbt_test OWNER = "dbt_user" TEMPLATE = "template0" ENCODING = 'UTF8'   CONNECTION LIMIT = -1;
```


#### 修改profiles.yml
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
      schema: jaffle_shop
      threads: 4

```

#### 修改dbt_project.yml
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
03:28:45    host: 123.xx.xx.53
03:28:45    port: 8000
03:28:45    user: dbt_user
03:28:45    database: dbt_test
03:28:45    schema: jaffle_shop
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
- 方法一：联系GaussDB技术支持，修改参数`password_encryption_type`为1。
- 方法二：参考下面的方法，使用GaussDB提供的psycopg2替换原生psycopg2。
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

使用下面的命令加载数据，数据文件位于`seeds/`目录下：
- raw_customers.csv
- raw_items.csv
- raw_supplies.csv
- raw_stores.csv
- raw_products.csv
- raw_orders.csv

会在GaussDB的数据库dbt_test.jaffle_shop中创建表raw开头的6张表，并加载数据：
```bash
dbt seed
```

数据导入成功会得到如下输出：
```bash
03:38:30  1 of 6 START seed file jaffle_shop.raw_customers ............................... [RUN]
03:38:30  2 of 6 START seed file jaffle_shop.raw_items ................................... [RUN]
03:38:30  3 of 6 START seed file jaffle_shop.raw_orders .................................. [RUN]
03:38:30  4 of 6 START seed file jaffle_shop.raw_products ................................ [RUN]
03:38:33  4 of 6 OK loaded seed file jaffle_shop.raw_products ............................ [INSERT 10 in 2.28s]
03:38:33  5 of 6 START seed file jaffle_shop.raw_stores .................................. [RUN]
03:38:34  1 of 6 OK loaded seed file jaffle_shop.raw_customers ........................... [INSERT 935 in 3.37s]
03:38:34  6 of 6 START seed file jaffle_shop.raw_supplies ................................ [RUN]
03:38:35  5 of 6 OK loaded seed file jaffle_shop.raw_stores .............................. [INSERT 6 in 1.93s]
03:38:36  6 of 6 OK loaded seed file jaffle_shop.raw_supplies ............................ [INSERT 65 in 1.87s]
03:40:25  2 of 6 OK loaded seed file jaffle_shop.raw_items ............................... [INSERT 90900 in 114.72s]
03:41:00  3 of 6 OK loaded seed file jaffle_shop.raw_orders .............................. [INSERT 61948 in 149.65s]
03:41:00
03:41:00  Finished running 6 seeds in 0 hours 2 minutes and 31.90 seconds (151.90s).
03:41:00
03:41:00  Completed successfully
03:41:00
03:41:00  Done. PASS=6 WARN=0 ERROR=0 SKIP=0 TOTAL=6
```

在GaussDB中查看数据：
```sql
ANALYZE jaffle_shop.raw_customers;
ANALYZE jaffle_shop.raw_items;
ANALYZE jaffle_shop.raw_orders;
ANALYZE jaffle_shop.raw_products;
ANALYZE jaffle_shop.raw_stores;
ANALYZE jaffle_shop.raw_supplies;

SELECT
    relname AS table_name,
    reltuples::BIGINT AS table_row_count
FROM
    pg_class c
JOIN
    pg_namespace n ON c.relnamespace = n.oid
WHERE
    n.nspname = 'jaffle_shop'
    AND c.relkind = 'r'  -- 只查询普通表
ORDER BY
    table_name;

```

输出结果：
| #   | table_name    | table_row_count |
|-----|---------------|-----------------|
| 1   | raw_customers | 935             |
| 2   | raw_items     | 90,900          |
| 3   | raw_orders    | 61,948          |
| 4   | raw_products  | 10              |
| 5   | raw_stores    | 6               |
| 6   | raw_supplies  | 65              |


### 运行项目

执行 `dbt run` 来运行项目,将raw开头的表经过数据清洗转换后加载到stg开头的表。
```bash
# 运行项目
dbt run

# 或者可以开启Debug模式，在运行过程中打印生成的每个 SQL 查询语句
dbt run -d --print
```
运行成功会得到如下输出：
```bash
... ...
03:54:30  Connection 'master' was properly closed.
03:54:30  Connection 'model.jaffle_shop.stg_supplies' was properly closed.
03:54:30  Connection 'model.jaffle_shop.stg_products' was properly closed.
03:54:30  Connection 'model.jaffle_shop.stg_order_items' was properly closed.
03:54:30  Connection 'model.jaffle_shop.stg_orders' was properly closed.
03:54:30
03:54:30  Finished running 6 table models in 0 hours 0 minutes and 4.02 seconds (4.02s).
03:54:30  Command end result
03:54:30
03:54:30  Completed successfully
03:54:30
03:54:30  Done. PASS=6 WARN=0 ERROR=0 SKIP=0 TOTAL=6
03:54:30  Resource report: {"command_name": "run", "command_success": true, "command_wall_clock_time": 5.962977, "process_in_blocks": "0", "process_kernel_time": 0.210429, "process_mem_max_rss": "111980", "process_out_blocks": "3344", "process_user_time": 5.56017}
03:54:30  Command `dbt run` succeeded at 11:54:30.798747 after 5.96 seconds
03:54:30  Sending event: {'category': 'dbt', 'action': 'invocation', 'label': 'end', 'context': [<snowplow_tracker.self_describing_json.SelfDescribingJson object at 0xffffb9f0ed90>, <snowplow_tracker.self_describing_json.SelfDescribingJson object at 0xffffb9b69dc0>, <snowplow_tracker.self_describing_json.SelfDescribingJson object at 0xffffb89f9910>]}
03:54:30  Flushing usage events
03:54:31  Sending 1 of 2
```

在GaussDB中查看数据：
```sql
ANALYZE jaffle_shop.stg_customers;
ANALYZE jaffle_shop.stg_order_items;
ANALYZE jaffle_shop.stg_orders;
ANALYZE jaffle_shop.stg_products;
ANALYZE jaffle_shop.stg_locations;
ANALYZE jaffle_shop.stg_supplies;

SELECT
    relname AS table_name,
    reltuples::BIGINT AS table_row_count
FROM
    pg_class c
JOIN
    pg_namespace n ON c.relnamespace = n.oid
WHERE
    n.nspname = 'jaffle_shop'
    AND c.relkind = 'r'  -- 只查询普通表
    AND c.relname like 'stg%' -- 只查询stg开头的表
ORDER BY
    table_name;
```


输出结果：
| #   | table_name       | table_row_count |
|-----|------------------|-----------------|
| 1   | stg_customers    | 935             |
| 2   | stg_locations    | 6               |
| 3   | stg_order_items  | 90,900          |
| 4   | stg_orders       | 61,948          |
| 5   | stg_products     | 10              |
| 6   | stg_supplies     | 65              |

（可选步骤）导出数据到csv文件：
```sql
-- 通过GaussDB客户端gsql登录，使用\copy命令导出数据到csv文件
\copy (select * from jaffle_shop.stg_customers) to '/tmp/stg_customers.csv' csv delimiter ',' quote '"';
\copy (select * from jaffle_shop.stg_locations) to '/tmp/stg_locations.csv' csv delimiter ',' quote '"';
\copy (select * from jaffle_shop.stg_order_items) to '/tmp/stg_order_items.csv' csv delimiter ',' quote '"';
\copy (select * from jaffle_shop.stg_orders) to '/tmp/stg_orders.csv' csv delimiter ',' quote '"';
\copy (select * from jaffle_shop.stg_products) to '/tmp/stg_products.csv' csv delimiter ',' quote '"';
\copy (select * from jaffle_shop.stg_supplies) to '/tmp/stg_supplies.csv' csv delimiter ',' quote '"';
```


## 基于Docker运行项目
### 前提条件

- docker已经安装
- 具备docker命令使用能力
- 克隆项目到本地（基于ARM架构），如果是x86架构，请修改Dockerfile中的FROM指令

```bash
# 构建镜像
docker build -t jaffle-shop-gaussdb:1.0.0  .

# 查看镜像
docker images

# 运行镜像，并进入容器(修改参数为实际的值)
docker run -it -e DB_HOST=xx.xx.xx.xx -e DB_USER=xxx -e DB_PASS=xxxx -e DB_NAME=xxxx --name jaffle-shop-gaussdb  jaffle-shop-gaussdb:1.0.0

# 如果是不带参数运行，则进入容器后需要修改profiles.yml
docker run -it --name jaffle-shop-gaussdb  jaffle-shop-gaussdb:1.0.0

```

### 测试连接

使用下面的命令测试连接

```bash
# 激活虚拟环境
source .venv/bin/activate

# 测试连接
dbt debug
```

如果连接成功，会输出类似下面的信息：
```bash
... ...
10:55:56  Connection:
10:55:56    host: 123.xx.xx.53
10:55:56    port: 8000
10:55:56    user: root
10:55:56    database: postgres
10:55:56    schema: jaffle_shop
10:55:56    connect_timeout: 10
10:55:56    role: None
10:55:56    search_path: None
10:55:56    keepalives_idle: 0
10:55:56    sslmode: None
10:55:56    sslcert: None
10:55:56    sslkey: None
10:55:56    sslrootcert: None
10:55:56    application_name: dbt
10:55:56    retries: 3
10:55:56  Registered adapter: gaussdbdws=1.0.1
10:55:56    Connection test: [OK connection ok]

10:55:56  All checks passed!
```

### 加载数据

使用下面的命令加载数据，数据文件位于`seeds/`目录下：
- raw_customers.csv
- raw_items.csv
- raw_supplies.csv
- raw_stores.csv
- raw_products.csv
- raw_orders.csv

会在GaussDB的数据库dbt_test.jaffle_shop中创建表raw开头的6张表，并加载数据：
```bash
dbt seed
```

数据导入成功会得到如下输出：
```bash
11:02:37  1 of 6 START seed file jaffle_shop.raw_customers ............................... [RUN]
11:02:38  1 of 6 OK loaded seed file jaffle_shop.raw_customers ........................... [INSERT 935 in 0.94s]
11:02:38  2 of 6 START seed file jaffle_shop.raw_items ................................... [RUN]
11:03:22  2 of 6 OK loaded seed file jaffle_shop.raw_items ............................... [INSERT 90900 in 44.07s]
11:03:22  3 of 6 START seed file jaffle_shop.raw_orders .................................. [RUN]
11:04:31  3 of 6 OK loaded seed file jaffle_shop.raw_orders .............................. [INSERT 61948 in 69.54s]
11:04:31  4 of 6 START seed file jaffle_shop.raw_products ................................ [RUN]
11:04:32  4 of 6 OK loaded seed file jaffle_shop.raw_products ............................ [INSERT 10 in 0.49s]
11:04:32  5 of 6 START seed file jaffle_shop.raw_stores .................................. [RUN]
11:04:32  5 of 6 OK loaded seed file jaffle_shop.raw_stores .............................. [INSERT 6 in 0.47s]
11:04:32  6 of 6 START seed file jaffle_shop.raw_supplies ................................ [RUN]
11:04:33  6 of 6 OK loaded seed file jaffle_shop.raw_supplies ............................ [INSERT 65 in 0.55s]
11:04:33  
11:04:33  Finished running 6 seeds in 0 hours 1 minutes and 58.26 seconds (118.26s).
11:04:33  
11:04:33  Completed successfully
11:04:33  
11:04:33  Done. PASS=6 WARN=0 ERROR=0 SKIP=0 TOTAL=6
```


在GaussDB中查看数据：
```sql
ANALYZE jaffle_shop.raw_customers;
ANALYZE jaffle_shop.raw_items;
ANALYZE jaffle_shop.raw_orders;
ANALYZE jaffle_shop.raw_products;
ANALYZE jaffle_shop.raw_stores;
ANALYZE jaffle_shop.raw_supplies;

SELECT
    relname AS table_name,
    reltuples::BIGINT AS table_row_count
FROM
    pg_class c
JOIN
    pg_namespace n ON c.relnamespace = n.oid
WHERE
    n.nspname = 'jaffle_shop'
    AND c.relkind = 'r'  -- 只查询普通表
ORDER BY
    table_name;

```

输出结果：
| #   | table_name    | table_row_count |
|-----|---------------|-----------------|
| 1   | raw_customers | 935             |
| 2   | raw_items     | 90,900          |
| 3   | raw_orders    | 61,948          |
| 4   | raw_products  | 10              |
| 5   | raw_stores    | 6               |
| 6   | raw_supplies  | 65              |


### 运行项目

执行 `dbt run` 来运行项目,将raw开头的表经过数据清洗转换后加载到stg开头的表。
```bash
# 运行项目
dbt run

# 或者可以开启Debug模式，在运行过程中打印生成的每个 SQL 查询语句
dbt run -d --print
```
运行成功会得到如下输出：
```bash
... ...
11:05:45  1 of 6 START sql table model jaffle_shop.stg_customers ......................... [RUN]
11:05:46  1 of 6 OK created sql table model jaffle_shop.stg_customers .................... [INSERT 0 935 in 0.63s]
11:05:46  2 of 6 START sql table model jaffle_shop.stg_locations ......................... [RUN]
11:05:46  2 of 6 OK created sql table model jaffle_shop.stg_locations .................... [INSERT 0 6 in 0.57s]
11:05:46  3 of 6 START sql table model jaffle_shop.stg_order_items ....................... [RUN]
11:05:47  3 of 6 OK created sql table model jaffle_shop.stg_order_items .................. [INSERT 0 90900 in 0.75s]
11:05:47  4 of 6 START sql table model jaffle_shop.stg_orders ............................ [RUN]
11:05:48  4 of 6 OK created sql table model jaffle_shop.stg_orders ....................... [INSERT 0 61948 in 0.93s]
11:05:48  5 of 6 START sql table model jaffle_shop.stg_products .......................... [RUN]
11:05:49  5 of 6 OK created sql table model jaffle_shop.stg_products ..................... [INSERT 0 10 in 0.54s]
11:05:49  6 of 6 START sql table model jaffle_shop.stg_supplies .......................... [RUN]
11:05:49  6 of 6 OK created sql table model jaffle_shop.stg_supplies ..................... [INSERT 0 65 in 0.54s]
11:05:50  
11:05:50  Finished running 6 table models in 0 hours 0 minutes and 5.83 seconds (5.83s).
11:05:50  
11:05:50  Completed successfully
11:05:50  
11:05:50  Done. PASS=6 WARN=0 ERROR=0 SKIP=0 TOTAL=6

# 退出容器
exit

```

在GaussDB中查看数据：
```sql
ANALYZE jaffle_shop.stg_customers;
ANALYZE jaffle_shop.stg_order_items;
ANALYZE jaffle_shop.stg_orders;
ANALYZE jaffle_shop.stg_products;
ANALYZE jaffle_shop.stg_locations;
ANALYZE jaffle_shop.stg_supplies;

SELECT
    relname AS table_name,
    reltuples::BIGINT AS table_row_count
FROM
    pg_class c
JOIN
    pg_namespace n ON c.relnamespace = n.oid
WHERE
    n.nspname = 'jaffle_shop'
    AND c.relkind = 'r'  -- 只查询普通表
    AND c.relname like 'stg%' -- 只查询stg开头的表
ORDER BY
    table_name;
```


输出结果：
| #   | table_name       | table_row_count |
|-----|------------------|-----------------|
| 1   | stg_customers    | 935             |
| 2   | stg_locations    | 6               |
| 3   | stg_order_items  | 90,900          |
| 4   | stg_orders       | 61,948          |
| 5   | stg_products     | 10              |
| 6   | stg_supplies     | 65              |

