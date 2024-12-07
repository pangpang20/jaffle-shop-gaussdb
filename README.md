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

查看版本信息
```bash

dbt --version

```

## 执行预处理脚本
修改profiles.yml
```bash
cp sample-profiles.yml profiles.yml
vi profiles.yml
jaffle_shop:
  target: dev_gaussdb
  outputs:
    dev_gaussdb:
      type: gaussdbdws
      host: xx.xx.xx.xx
      user:
      password:
      port: 8000
      dbname:
      schema:
      threads: 4

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

