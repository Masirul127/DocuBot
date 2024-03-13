from fastapi import FastAPI, HTTPException,File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import List
import os
import re
import pdfplumber
import pandas as pd
import psycopg2
from sqlalchemy import create_engine, Table, MetaData, Column, Integer, String
from sqlalchemy.exc import SQLAlchemyError

# Import your existing PDF extraction code
from extract_key_value import Extraction
from extract_table import ExtractTable
from transaction import Transaction

app = FastAPI(debug=True,
              docs_url='/extract/docs',
              redoc_url='/extract/redoc',
              openapi_url='/extract/openapi.json')

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

conn = psycopg2.connect(
    dbname="Docubot",
    user="postgres",
    password="postgres",
    host="localhost",
    port="5432"
)
engine = create_engine('postgresql://postgres:postgres@localhost/Docubot')

class PDFPath(BaseModel):
    path: str

class Details(BaseModel):
    message: str

class Transactions(BaseModel):
    message: str

class Rating(BaseModel):
    message: str

class Uploaddocument(BaseModel):
    message: str

UPLOAD_FOLDER = './uploads'
isdir = os.path.isdir(UPLOAD_FOLDER)
if not isdir:
    os.makedirs(UPLOAD_FOLDER)

extract = Extraction()
transaction = ExtractTable()
expenditure = Transaction()

@app.get('/', include_in_schema=False)
def index():
    return RedirectResponse('extract/docs')

def insert_details(details):
    try:
        cur = conn.cursor()
        for column_name, value in details.items():
            cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='extraction_key_value' AND column_name=%s", (column_name,))
            exists = cur.fetchone()
            if not exists:
                cur.execute(f"ALTER TABLE extraction_key_value ADD COLUMN {column_name} TEXT;")
        insert_query = f"INSERT INTO extraction_key_value ({', '.join(details.keys())}) VALUES ({', '.join(['%s']*len(details))})"
        cur.execute(insert_query, list(details.values()))
        conn.commit()
    except psycopg2.Error as e:
        # Log or handle the error
        print(f"Error inserting details: {e}")
        # Rollback the transaction
        conn.rollback()
    finally:
        cur.close()
        
def create_or_update_transaction_table(trans, engine):
    metadata = MetaData()
    table_name = 'extract_transaction_data'
    table = Table(table_name, metadata,Column('id', Integer, primary_key=True, autoincrement=True), extend_existing=True)
    for column_name in trans[0].keys():
        column_type = Integer if isinstance(trans[0][column_name], int) else String
        if column_name not in table.columns:
            table.append_column(Column(column_name, column_type))

    metadata.create_all(engine)

    with engine.begin() as conn:
        try:
            for row in trans:
                insert_statement = table.insert().values(**row)
                conn.execute(insert_statement)
        except SQLAlchemyError as e:
            # Log or handle the error
            print(f"Error inserting details: {e}")
            # Rollback the transaction if needed
            conn.rollback()

def get_docname(docid):
    cursor = conn.cursor()
    query = "SELECT docname FROM loadedfiles WHERE id = %s"
    cursor.execute(query, (docid,))
    docname = cursor.fetchone()  # Fetch the first column of the first row
    cursor.close()
    return docname[0] if docname else None

def loadedfiles_id(applno):
    cursor = conn.cursor()
    query = "SELECT id FROM loadedfiles WHERE applno = %s"
    cursor.execute(query, (applno,))
    ids = cursor.fetchall()
    cursor.close()
    return ids

def get_key_value_id(docid):
    cursor = conn.cursor()
    query = "SELECT docid FROM extraction_key_value WHERE docid = %s"
    cursor.execute(query, (docid,))
    match_id = cursor.fetchone()
    cursor.close()
    return match_id[0] if match_id else None

def get_key_value_data(account_num):
    cursor = conn.cursor()
    query = "SELECT docid,accountno,statementperiod,statementperiodfrom,statementperiodto FROM extraction_key_value WHERE accountno = %s"
    cursor.execute(query, (account_num,))
    match_id = cursor.fetchone()
    cursor.close()
    if match_id:
        return {
            "docid" :match_id[0],
            "accountno": match_id[1],
            "statementperiod": match_id[2],
            "statementperiodfrom": match_id[3],
            "statementperiodto": match_id[4]
        }
    else:
        return None

def get_transaction_id(docid):
    cursor = conn.cursor()
    query = "SELECT docid FROM extract_transaction_data WHERE docid = %s"
    cursor.execute(query, (docid,))
    match_id = cursor.fetchone()
    cursor.close()
    return match_id[0] if match_id else None

def get_transaction_data(ids):
    all_data = []
    cursor = conn.cursor()
    query = "SELECT * FROM extract_transaction_data WHERE docid IN %s"
    cursor.execute(query, (tuple(ids),))
    rows = cursor.fetchall()
    for row in rows:
        all_data.append(row)

    cursor.close()
    return all_data

def get_emi(applno):
    cursor = conn.cursor()
    query = "SELECT emi FROM loandetails WHERE applno = %s"
    cursor.execute(query, (applno,))
    emi = cursor.fetchone()[0]  # Fetch the first column of the first row
    cursor.close()
    return emi

def update_loan_details(applno,gross_income,expenses,emi):
    if gross_income <= 0:
        raise ValueError("Income must be greater than 0")
    
    cursor = conn.cursor()
    query = "UPDATE loandetails SET income = %s, expenses = %s, rir = (%s/ %s) * 100.00 WHERE applno = %s AND %s > 0"
    cursor.execute(query, (gross_income, expenses,emi, gross_income, applno, gross_income))
    conn.commit()
    cursor.close()

def insert_loadedfiles_path(applno, filepath):
    try:
        cursor = conn.cursor()
        query = "INSERT INTO loadedfiles (applno, docname) VALUES (%s, %s)"
        cursor.execute(query, (applno, filepath))
        conn.commit()
    except Exception as e:
        print(f"Error inserting record: {e}")
        conn.rollback()
    finally:
        cursor.close()

def rating_calculation(applno):
    cur = conn.cursor()
    all_data = []
    sql_query = """
    select 'Expense', case b.weight when 0 then b.points else a.expenses * weight end from LoanDetails a, critlookup b where a.expenses >= b.rangelo and a.expenses < b.rangehi  and b.critcat = 'Expenses' and a.applno = applno
    union
    select 'Income', case b.weight when 0 then b.points else a.income * weight end from LoanDetails a, critlookup b where a.income >= b.rangelo and a.income < b.rangehi  and b.critcat = 'Gross Income'  and a.applno = applno
    union
    select 'Cheque Bounce', case b.weight when 0 then b.points else a.bounced * weight end from LoanDetails a, critlookup b where a.bounced >= b.rangelo and a.bounced < b.rangehi  and b.critcat = 'Cheque Bounce'  and a.applno = applno
    union
    select 'Delayed Payment', case b.weight when 0 then b.points else a.delayed * weight end from LoanDetails a, critlookup b where a.delayed >= b.rangelo and a.delayed < b.rangehi  and b.critcat = 'Delayed Payment'  and a.applno = applno
    union
    select 'RIR', case b.weight when 0 then b.points else a.rir * weight end from LoanDetails a, critlookup b where a.rir >= b.rangelo and a.rir < b.rangehi  and b.critcat = 'RIR'  and a.applno = applno
    """
    cur.execute(sql_query)
    rows = cur.fetchall()
    
    for row in rows:
        all_data.append(row)

    total_score = sum(row[1] for row in all_data)

    update_query = "UPDATE loandetails SET rating = %s WHERE applno = applno;"
    cur.execute(update_query, (total_score/4,))
    conn.commit()
    cur.close()

@app.post("/extract/uploaddocument/")
async def uploaddocument(applno: str,files: List[UploadFile] = File(...)):
    try:
        for file in files:
            name = file.filename.split('.')[0]
            ext = file.filename.split('.')[-1]
            file_path = f'{UPLOAD_FOLDER}/{name}.{ext}'
            with open(file_path, 'wb+') as f:
                f.write(file.file.read())
            f.close()

            insert_loadedfiles_path(applno,file_path)
        message = "Documents and its applno are inserted in the loadedfiles table successfully"
    except Exception as e:
        message = f"Error In Uploading Documents and its applno: {str(e)}"

    return Uploaddocument(message=message) 

@app.post("/extract/extract_details/")
async def extract_details(docid: int):
    message = "Default message"
    get_id = get_key_value_id(docid)
    if get_id == docid:
        raise HTTPException(status_code=200, detail="Details Already extracted and inserted into the DB")

    pdf_path = get_docname(docid)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    try:
        details = {}
        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            info = first_page.extract_text()
        bankname1 = re.search(r'INDIAN BANK', info)
        details['bankname'] = bankname1.group(0) if bankname1 else "Not Found"
        for key, value in details.items():
            details[key] = value

        if details[key] == 'INDIAN BANK':
            bank = 'INDIAN BANK'
        else:
            bank = extract.classify_bank(info)

        if bank == "STATE BANK OF INDIA":
            index = info.find('Search for')
            if index != -1:
                details = extract.extract_key_value_sbi_yono(info)
                details['docid'] = docid
                details['bankname'] = bank
                account_num = details['accountno']
            else:
                details = extract.extract_key_value_sbi(info)
                details['address'] = details['address'].replace("\n", " ")
                details['docid'] = docid
                details['bankname'] = bank
                account_num = details['accountno']
            check_data_present = get_key_value_data(account_num)
            if check_data_present is not None and details.get('statementperiod') == check_data_present.get('statementperiod'):
                raise HTTPException(status_code=409, detail=f"Details for docid {check_data_present.get('docid')} already present in the DB")
            insert_details(details)

        elif bank == "HDFC Bank":
            details = extract.extract_key_value_hdfc(info)
            details['bankaddress'] = details['bankaddress'].replace("\n", " ")
            details['docid'] = docid
            details['bankname'] = bank
            account_num = details['accountno']
            check_data_present = get_key_value_data(account_num)
            if check_data_present is not None and details.get('statementperiodfrom') == check_data_present.get('statementperiodfrom') and details.get('statementperiodto') == check_data_present.get('statementperiodto'):
                raise HTTPException(status_code=409, detail=f"Details for docid {check_data_present.get('docid')} already present in the DB")
            insert_details(details)

        elif bank == "INDIAN BANK":
            details = extract.extract_key_value_indian(info)
            details['address'] = ', '.join(details['address'])
            details['docid'] = docid
            details['bankname'] = bank
            account_num = details['accountno']
            check_data_present = get_key_value_data(account_num)
            if check_data_present is not None and details.get('statementperiod') == check_data_present.get('statementperiod'):
                raise HTTPException(status_code=409, detail=f"Details for docid {check_data_present.get('docid')} already present in the DB")
            insert_details(details)

        elif bank == "UNION BANK OF INDIA":
            details = extract.extract_key_value_union(info)
            details['docid'] = docid
            details['bankname'] = bank
            account_num = details['accountno']
            check_data_present = get_key_value_data(account_num)
            if check_data_present is not None and details.get('statementperiodfrom') == check_data_present.get('statementperiodfrom') and details.get('statementperiodto') == check_data_present.get('statementperiodto'):
                raise HTTPException(status_code=409, detail=f"Details for docid {check_data_present.get('docid')} already present in the DB")
            insert_details(details)

        elif bank == "BANK OF BARODA":
            text_with_coords_bob = first_page.extract_table({"vertical_strategy": "text","horizontal_strategy": "text","min_words_vertical": 2})
            details = extract.extract_key_value_bob(text_with_coords_bob)
            details['docid'] = docid
            details['bankname'] = bank
            account_num = details['accountno']
            check_data_present = get_key_value_data(account_num)
            if check_data_present is not None and details.get('statementperiod') == check_data_present.get('statementperiod'):
                raise HTTPException(status_code=409, detail=f"Details for docid {check_data_present.get('docid')} already present in the DB")
            insert_details(details)

        elif bank == "AXIS BANK":
            details = extract.extract_key_value_axis(info)
            details['docid'] = docid
            details['bankname'] = bank
            account_num = details['accountno']
            check_data_present = get_key_value_data(account_num)
            if check_data_present is not None and details.get('statementperiodfrom') == check_data_present.get('statementperiodfrom') and details.get('statementperiodto') == check_data_present.get('statementperiodto'):
                raise HTTPException(status_code=409, detail=f"Details for docid {check_data_present.get('docid')} already present in the DB")
            insert_details(details)

        elif bank == "YES BANK":
            details = extract.extract_key_value_yes(info)
            details['docid'] = docid
            details['bankname'] = bank
            account_num = details['accountno']
            check_data_present = get_key_value_data(account_num)
            if check_data_present is not None and details.get('statementperiod') == check_data_present.get('statementperiod'):
                raise HTTPException(status_code=409, detail=f"Details for docid {check_data_present.get('docid')} already present in the DB")
            insert_details(details)
        else:
            raise ValueError("Bank not supported")

        message = "Details extracted successfully"
    
    except HTTPException as e:
        raise e
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PDF file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting details: {str(e)}")

    return Details(message=message)
    

@app.post("/extract/extract_transactions/")
async def extract_transactions(docid: int):
    transaction_id = get_transaction_id(docid)
    if transaction_id == docid:
        raise HTTPException(status_code=200, detail="Table Data Already parsed and inserted into the DB")

    duplicate_insertion = get_key_value_id(docid)
    if duplicate_insertion is None:
        raise HTTPException(status_code=409, detail="Transaction data cannot be  parsed as Key_values are not parsed for this docid.")

    pdf_path = get_docname(docid)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    try:
        details = {}
        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            info = first_page.extract_text()
        bankname1 = re.search(r'INDIAN BANK', info)
        details['bankname1'] = bankname1.group(0) if bankname1 else "Not Found"
        for key, value in details.items():
            details[key] = value

        if details[key] == 'INDIAN BANK':
            bank = 'INDIAN BANK'
        else:
            bank = extract.classify_bank(info)

        if bank == "STATE BANK OF INDIA":
            index = info.find('Search for')
            if index != -1:
                trans = transaction.extract_table_sbi(pdf_path)
                columns =['Txn_Date','Description','ChequeNumber','Debit','Credit','Balance']
                df = pd.DataFrame(trans, columns=columns)
                df['docid'] = docid
                df['bankname'] = bank
                df = df[df['Description'] != 'Details']
                df['Txn_Date'] = pd.to_datetime(df['Txn_Date'], format='%d %b %Y', errors='coerce')
                trans = df.to_dict(orient='records')
                create_or_update_transaction_table(trans,engine)
            else:
                trans = transaction.extract_table_sbi(pdf_path)
                columns =['Txn_Date','Value_Date','Description','ChequeNumber','Debit','Credit','Balance']
                df = pd.DataFrame(trans, columns=columns)
                df['docid'] = docid
                df['bankname'] = bank
                df = df[df['Txn_Date'] != 'Txn Date']
                df['Txn_Date'] = pd.to_datetime(df['Txn_Date'], format='%d %b %Y', errors='coerce')
                trans = df.to_dict(orient='records')
                create_or_update_transaction_table(trans,engine)

        elif bank == "HDFC Bank":
            trans = transaction.extract_table_hdfc(pdf_path)
            trans['docid'] = docid
            trans['bankname'] = bank
            trans = trans.to_dict(orient='records')
            create_or_update_transaction_table(trans,engine)

        elif bank == "INDIAN BANK":
            trans = transaction.extract_table_indian(pdf_path)
            columns =['Txn_Date','Value_Date','RemitterBranch','Description','ChequeNumber','Debit','Credit','Balance']
            df = pd.DataFrame(trans, columns=columns)
            df['docid'] = docid
            df['bankname'] = bank
            df = df[df['Txn_Date'] != 'Value\nDate']
            df['Txn_Date'] = df['Txn_Date'].astype(str).str.replace('\n', '')
            df['Value_Date'] = df['Value_Date'].astype(str).str.replace('\n', '')
            df['Txn_Date'] = df['Txn_Date'].replace('', '01/01/2018')
            df['Txn_Date'] = pd.to_datetime(df['Txn_Date'].str.strip(), format='%d/%m/%Y', errors='coerce')
            df = df[df['Txn_Date'].notnull()]
            trans = df.to_dict(orient='records')
            create_or_update_transaction_table(trans,engine)

        elif bank == "UNION BANK OF INDIA":
            trans = transaction.extract_table_union(pdf_path)
            columns =['SerialNo','Txn_Date','TransactionId','Description','Amount','Balance']
            df = pd.DataFrame(trans, columns=columns)
            df['Debit'] = df['Amount'].apply(lambda x: x.split(' ')[0] if '(Dr)' in x else '')
            df['Credit'] = df['Amount'].apply(lambda x: x.split(' ')[0] if '(Cr)' in x else '')
            df['docid'] = docid
            df['bankname'] = bank
            df['Txn_Date'] = pd.to_datetime(df['Txn_Date'].str.strip(), format='%d/%m/%Y',errors='coerce')
            df = df[df['Txn_Date'].notnull()]
            trans = df.to_dict(orient='records')
            create_or_update_transaction_table(trans,engine)

        elif bank == "BANK OF BARODA":
            trans = transaction.extract_table_bob(pdf_path)
            trans = [[row[0].split(' ')[0], row[0].split(' ')[1]] + row[1:] if row[0] is not None and ' ' in row[0] else row for row in trans]
            columns =['SerialNo','Txn_Date','Value_Date','Description','Debit','Credit','Balance']
            df = pd.DataFrame(trans, columns=columns)
            df['docid'] = docid
            df['bankname'] = bank
            df['Txn_Date'] = pd.to_datetime(df['Txn_Date'].str.strip(), format='%d-%m-%Y',errors='coerce')
            df = df[df['Txn_Date'].notnull()]
            trans = df.to_dict(orient='records')
            create_or_update_transaction_table(trans,engine)

        elif bank == "AXIS BANK":
            trans = transaction.extract_table_axis(pdf_path)
            columns =['Txn_Date','ChequeNumber','Description','Debit','Credit','Balance','Init.Br']
            df = pd.DataFrame(trans, columns=columns)
            df['docid'] = docid
            df['bankname'] = bank
            df['Txn_Date'] = pd.to_datetime(df['Txn_Date'].str.strip(), format='%d-%m-%Y', errors='coerce')
            df = df[df['Txn_Date'].notnull()]
            trans = df.to_dict(orient='records')
            create_or_update_transaction_table(trans,engine)

        elif bank == "YES BANK":
            trans = transaction.extract_table_yes(pdf_path)
            columns =['Txn_Date','Value_Date','Description','Debit','Credit','Balance']
            df = pd.DataFrame(trans, columns=columns)
            df['docid'] = docid
            df['bankname'] = bank
            df['Txn_Date'] = pd.to_datetime(df['Txn_Date'].str.strip(), format='%d/%m/%Y', errors='coerce')
            df = df[df['Txn_Date'].notnull()]
            trans = df.to_dict(orient='records')
            create_or_update_transaction_table(trans,engine)
        else:
            raise ValueError("Bank not supported")

        message = "Transactions extracted successfully"

    except HTTPException as e:
        raise e
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PDF file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting details: {str(e)}")

    return Details(message=message)

@app.post("/extract/rating/")
async def rating(applno: str):
    try:
        ids = loadedfiles_id(applno)
        trans = get_transaction_data(ids)
        months = expenditure.distinct_months(trans)
        expd = expenditure.classify_trans(trans)
        data = expenditure.money(expd)
        gross_income = expenditure.repeated_credits(data,months)
        expenses = expenditure.repeated_debits(data,months)
        emi = get_emi(applno)
        update_loan_details(applno,gross_income,expenses,emi)
        rating_calculation(applno)
        message = "Rating calculated and updated in loanDetails table successfully"
    except Exception as e:
        message = f"Error In Calculating Rating engine: {str(e)}"

    return Rating(message=message)