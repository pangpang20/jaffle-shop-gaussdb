import psycopg2
import os
import yaml
import csv
import shutil
from tqdm import tqdm

class DataTrans:
    def __init__(self, profiles_path):
        self.current_directory = os.getcwd()
        self.profiles_path = os.path.join(self.current_directory, profiles_path)
        self.source_data_directory = os.path.join(self.current_directory, 'source_data') 
        self.tables = [
            'stg_customers',
            'stg_locations',
            'stg_order_items',
            'stg_orders',
            'stg_products',
            'stg_supplies'
        ]
        self.src_host = None
        self.src_user = None
        self.src_pass = None
        self.src_port = None
        self.src_dbname = None
        self.src_schema = None
        self.tag_host = None
        self.tag_user = None
        self.tag_pass = None
        self.tag_port = None
        self.tag_dbname = None
        self.tag_schema = None
        self.load_profiles()

    def load_profiles(self): 
        try:
            with open(self.profiles_path, 'r') as file:
                profiles = yaml.safe_load(file)
        except FileNotFoundError as e:
            print(f"Error: {self.profiles_path} file not found. {e}")
            raise
        except yaml.YAMLError as e:
            print(f"Error parsing {self.profiles_path}. {e}")
            raise

        source = profiles['transform']['source']
        self.src_host = source['host']
        self.src_user = source['user']
        self.src_pass = source['password']
        self.src_port = source['port']
        self.src_dbname = source['dbname']
        self.src_schema = source['schema'] 

        target = profiles['transform']['target']
        self.tag_host = target['host']
        self.tag_user = target['user']
        self.tag_pass = target['password']
        self.tag_port = target['port']
        self.tag_dbname = target['dbname']
        self.tag_schema = target['schema'] 

        if not all([self.src_host, self.src_user, self.src_pass, self.src_port, self.src_dbname,self.src_schema]):
            raise ValueError("Missing required source database connection information in trans_settings.yml")

        if not all([self.tag_host, self.tag_user, self.tag_pass, self.tag_port, self.tag_dbname,self.tag_schema]):
            raise ValueError("Missing required target database connection information in trans_settings.yml")

        print("Profiles loaded successfully.")

    def create_source_data_directory(self):
        if os.path.exists(self.source_data_directory):
            shutil.rmtree(self.source_data_directory) 
        os.makedirs(self.source_data_directory) 

    def connect_to_gaussdb(self):
        try:
            conn = psycopg2.connect(database=self.src_dbname, user=self.src_user, password=self.src_pass, host=self.src_host, port=self.src_port)
            cur = conn.cursor()  
            cur.execute(f'SET search_path TO {self.src_schema};')
            print("Connection to gaussdb established successfully!")
            return conn, cur
             
        except psycopg2.DatabaseError as e:
            print(f"Error: Unable to connect to the database. {e}")
            raise

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise
    def connect_to_dws(self):
        try:
            conn = psycopg2.connect(database=self.tag_dbname, user=self.tag_user, password=self.tag_pass, host=self.tag_host, port=self.tag_port)
            cur = conn.cursor()  
            cur.execute(f'SET search_path TO {self.tag_schema};')
            print("Connection to dws established successfully!")
            return conn, cur
             
        except psycopg2.DatabaseError as e:
            print(f"Error: Unable to connect to the database. {e}")
            raise

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise
 
        
    def fetch_data_from_gaussdb(self,cur,table):
        cur.execute(f'SELECT * FROM {table};')
        rows = cur.fetchall()
        column_names = [desc[0] for desc in cur.description]
        return rows, column_names
    
    def write_data_to_csv(self,rows,column_names,table):
        csv_file_path = os.path.join(self.source_data_directory, f'{table}.csv')

        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(column_names)
            for row in tqdm(rows, desc=f"Writing {table}", unit="row"):
                csv_writer.writerow(row)

        print(f"Data from {table} has been written to {table}.csv")
        
    def fetch_table_ddl(self,cur,table):
        cur.execute(f"""
            SELECT 
                'DROP TABLE IF EXISTS '|| table_name ||'; \nCREATE TABLE ' || table_name || ' (' || 
                LISTAGG(column_name || ' ' || data_type, ', ') WITHIN GROUP (ORDER BY ordinal_position) || ');' ddl
            FROM 
                information_schema.columns
            WHERE 
                table_schema = '{self.src_schema}'
                AND table_name = '{table}'
            GROUP BY 
                table_name;
        """)
        ddl = cur.fetchone()[0]
        return ddl
    
    def convert_to_dws_ddl(self, ddl):
        ddl = ddl.replace('varchar', 'STRING')  
        ddl = ddl.replace('int', 'INT')   
        return ddl
    
    def write_ddl_to_sql_file(self, ddls):
        sql_file_path = os.path.join(self.current_directory, 'dws_create_stg_tables.sql')
        with open(sql_file_path, 'w', encoding='utf-8') as file:
            file.write(f"CREATE SCHEMA IF NOT EXISTS {self.tag_schema};\n\n")
            for ddl in ddls:                
                file.write(f"{ddl}\n\n")
        print(f"DDL statements have been written to {sql_file_path}")
        
    def extract_data_and_ddl(self):
        self.create_source_data_directory()
        conn, cur = self.connect_to_gaussdb()
        ddls = []
        for table in self.tables:
            rows, column_names = self.fetch_data_from_gaussdb(cur,table)
            self.write_data_to_csv(rows,column_names,table)
            
            ddl=self.fetch_table_ddl(cur,table)
            dws_ddl = self.convert_to_dws_ddl(ddl)
            ddls.append(dws_ddl)
            
        self.write_ddl_to_sql_file(ddls)

        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        print("Connection and cursor closed.")
    
    
    def exec_dws_ddl(self):
        conn,cur=self.connect_to_dws()
        ddl_path=os.path.join(self.current_directory, 'dws_create_stg_tables.sql')
        with open(ddl_path,'r',encoding='utf-8') as f:
            sql_script = f.read()
            cur.execute(sql_script)
            conn.commit()
            print("DDL executed successfully.")
            
    
    def import_csv_to_table(self,conn,cur,table):
        
        csv_file_path = os.path.join(self.source_data_directory, f'{table}.csv')
        print(f"Importing data from {csv_file_path} into dws...")

        with open(csv_file_path,'r',encoding='utf-8') as f:
            next(f)
            copy_sql = f"""
                COPY {self.tag_schema}.{table} FROM stdin WITH CSV HEADER DELIMITER as ',';
            """
            cur.copy_expert(sql=copy_sql, file=f)
            conn.commit()
            print(f"Data for {table} imported successfully.")
         
    def load_data_to_dws(self):
        conn,cur=self.connect_to_dws()
        for table in self.tables:
            self.import_csv_to_table(conn,cur,table)
        
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        print("Connection and cursor closed.")
        
def main(profiles_path='trans_settings.yml'):
    dataTrans = DataTrans(profiles_path)
    dataTrans.extract_data_and_ddl()
    dataTrans.exec_dws_ddl()
    dataTrans.load_data_to_dws()
        
if __name__ == "__main__":
    main()