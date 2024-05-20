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
    dbname="rating",
    user="postgres",
    password="postgres",
    host="localhost",
    port="5432"
)
engine = create_engine('postgresql://postgres:postgres@localhost/rating')

class PDFPath(BaseModel):
    path: str

class Details(BaseModel):
    message: str

class Transactions(BaseModel):
    message: str

class Rating(BaseModel):
    message: str

class InsertedFile(BaseModel):
    id: int
    file_path: str

class Uploaddocument(BaseModel):
    message: str
    inserted_ids: List[InsertedFile]

UPLOAD_FOLDER = './uploads'
isdir = os.path.isdir(UPLOAD_FOLDER)
if not isdir:
    os.makedirs(UPLOAD_FOLDER)

current_permissions = os.stat(UPLOAD_FOLDER).st_mode & 0o777
if current_permissions != 0o777:
    os.chmod(UPLOAD_FOLDER, 0o777)

extract = Extraction()
transaction = ExtractTable()
expenditure = Transaction()

@app.get('/', include_in_schema=False)
def index():
    return RedirectResponse('extract/docs')

def insert_details(conn,details):
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

def get_docname(conn, docid):
    cursor = None
    try:
        cursor = conn.cursor()
        query = "SELECT docname FROM loadedfiles WHERE id = %s"
        cursor.execute(query, (docid,))
        docname_row = cursor.fetchone()
        if docname_row is not None:
            return docname_row[0]  # Fetch the docname value from the first column
        else:
            return None 
    except Exception as e:
        print(f"Error fetching data: {e}")
        conn.rollback()
        return None
    finally:
        if cursor is not None:
            cursor.close()

def loadedfiles_id(conn, applno):
    cursor = None
    try:
        cursor = conn.cursor()
        query = "SELECT id FROM loadedfiles WHERE applno = %s"
        cursor.execute(query, (applno,))
        ids = cursor.fetchall()
        return ids
    except Exception as e:
        print(f"Error fetching data: {e}")
        conn.rollback()
        return []
    finally:
        if cursor is not None:
            cursor.close()

def get_key_value_id(conn, docid):
    cursor = None
    try:
        cursor = conn.cursor()
        query = "SELECT docid FROM extraction_key_value WHERE docid = %s"
        cursor.execute(query, (docid,))
        match_id = cursor.fetchone()
        return match_id[0] if match_id else None
    except Exception as e:
        print(f"Error fetching data: {e}")
        conn.rollback()
        return None
    finally:
        if cursor is not None:
            cursor.close()

def get_key_value_data(conn, account_num):
    cursor = None
    try:
        cursor = conn.cursor()
        query = "SELECT docid, accountno, statementperiod, statementperiodfrom, statementperiodto FROM extraction_key_value WHERE accountno = %s"
        cursor.execute(query, (account_num,))
        match_id = cursor.fetchone()
        if match_id:
            return {
                "docid": match_id[0],
                "accountno": match_id[1],
                "statementperiod": match_id[2],
                "statementperiodfrom": match_id[3],
                "statementperiodto": match_id[4]
            }
        else:
            return None
    except Exception as e:
        print(f"Error fetching data: {e}")
        conn.rollback()
        return None
    finally:
        if cursor is not None:
            cursor.close()

def get_loadedfiles_data(conn, file_path, applno):
    cursor = None
    try:
        cursor = conn.cursor()
        query = "SELECT id, applno FROM loadedfiles WHERE docname = %s and applno = %s"
        cursor.execute(query, (file_path,applno))
        match_id = cursor.fetchone()
        if match_id:
            return {
                "docid": match_id[0],
                "applno": match_id[1]
            }
        else:
            return None
    except Exception as e:
        print(f"Error fetching data: {e}")
        conn.rollback()
        return None
    finally:
        if cursor is not None:
            cursor.close()

def get_transaction_id(conn, docid):
    cursor = None
    try:
        cursor = conn.cursor()
        query = "SELECT docid FROM extract_transaction_data WHERE docid = %s"
        cursor.execute(query, (docid,))
        match_id = cursor.fetchone()
        return match_id[0] if match_id else None
    except Exception as e:
        print(f"Error fetching data: {e}")
        conn.rollback()
        return None
    finally:
        if cursor is not None:
            cursor.close()

def get_transaction_data(conn, ids):
    all_data = []
    cursor = None
    try:
        cursor = conn.cursor()
        if not ids:
            return all_data
        query = "SELECT * FROM extract_transaction_data WHERE docid IN %s"
        cursor.execute(query, (tuple(ids),))
        rows = cursor.fetchall()
        for row in rows:
            all_data.append(row)
    except Exception as e:
        print(f"Error fetching data: {e}")
        conn.rollback()
    finally:
        if cursor is not None:
            cursor.close()
    return all_data

def get_emi(conn, applno):
    cursor = None
    try:
        cursor = conn.cursor()
        query = "SELECT emi FROM loandetails WHERE applno = %s"
        cursor.execute(query, (applno,))
        emi_row = cursor.fetchone()
        if emi_row is not None:
            return emi_row[0]  # Fetch the emi value from the first column
        else:
            return None
    except Exception as e:
        print(f"Error fetching data: {e}")
        conn.rollback()
        return None
    finally:
        if cursor is not None:
            cursor.close()

def update_loan_details(conn,applno, gross_income, expenses, emi):
    if gross_income <= 0:
        raise ValueError("Income must be greater than 0")
    
    try:
        cursor = conn.cursor()
        query = "UPDATE loandetails SET income = %s, expenses = %s, rir = (%s / %s) * 100.00 WHERE applno = %s"
        cursor.execute(query, (gross_income, expenses, emi, gross_income, applno))
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error updating loan details: {error}")
        conn.rollback()
    finally:
        cursor.close()


def insert_loadedfiles_path(conn,applno, filepath):
    cursor = None
    try:
        cursor = conn.cursor()
        query = "INSERT INTO loadedfiles (applno, docname) VALUES (%s, %s) RETURNING id"
        cursor.execute(query, (applno, filepath))
        inserted_id = cursor.fetchone()[0]
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as e:
        print(f"Error inserting record: {e}")
        conn.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
    return inserted_id

def rating_calculation(conn, applno):
    cur = None
    try:
        cur = conn.cursor()
        sql_query = """
        SELECT
            SUM(CASE WHEN b.critcat = 'Expenses' THEN CASE WHEN b.weight = 0 THEN b.points ELSE a.expenses * b.weight END ELSE 0 END) +
            SUM(CASE WHEN b.critcat = 'Gross Income' THEN CASE WHEN b.weight = 0 THEN b.points ELSE a.income * b.weight END ELSE 0 END) +
            SUM(CASE WHEN b.critcat = 'Cheque Bounce' THEN CASE WHEN b.weight = 0 THEN b.points ELSE a.bounced * b.weight END ELSE 0 END) +
            SUM(CASE WHEN b.critcat = 'Delayed Payment' THEN CASE WHEN b.weight = 0 THEN b.points ELSE a.delayed * b.weight END ELSE 0 END) +
            SUM(CASE WHEN b.critcat = 'RIR' THEN CASE WHEN b.weight = 0 THEN b.points ELSE a.rir * b.weight END ELSE 0 END)
        FROM LoanDetails a
        JOIN critlookup b ON (a.expenses BETWEEN b.rangelo AND b.rangehi AND b.critcat = 'Expenses')
                          OR (a.income BETWEEN b.rangelo AND b.rangehi AND b.critcat = 'Gross Income')
                          OR (a.bounced BETWEEN b.rangelo AND b.rangehi AND b.critcat = 'Cheque Bounce')
                          OR (a.delayed BETWEEN b.rangelo AND b.rangehi AND b.critcat = 'Delayed Payment')
                          OR (a.rir BETWEEN b.rangelo AND b.rangehi AND b.critcat = 'RIR')
        WHERE a.applno = %s
        """
        cur.execute(sql_query, (applno,))
        total_score = cur.fetchone()[0] / 4
        if total_score > 900:
            rating = 885
        else:
            rating = total_score
        update_query = "UPDATE loandetails SET rating = %s WHERE applno = %s;"
        cur.execute(update_query, (rating, applno))
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error updating loan details: {error}")
        conn.rollback()
    finally:
        if cur is not None:
            cur.close()

def delete_data_by_docid(conn, docids):
    cur = None
    try:
        cur = conn.cursor()
        # Delete from extraction_key_value
        cur.execute("DELETE FROM extraction_key_value WHERE docid IN %s", (tuple(docids),))
        # Delete from extract_transaction_data
        cur.execute("DELETE FROM extract_transaction_data WHERE docid IN %s", (tuple(docids),))
        conn.commit()
        print("Data deleted successfully.")
    except psycopg2.Error as e:
        print(f"Error deleting data: {e}")
        conn.rollback()
    finally:
        if cur is not None:
            cur.close()

def filter_unique_records(data):
    # Convert the data to a DataFrame
    df = pd.DataFrame(data, columns=['id','docid','SerialNo','TransactionId','Txn_Date','Value_Date','Description','ChequeNumber','Amount','Debit','Credit','Balance','Init.Br','bankname','RemitterBranch'])

    # Drop duplicates excluding the first and second column
    unique_df = df.iloc[:, 2:].drop_duplicates()

    # Convert the DataFrame back to a list of tuples
    unique_records = unique_df.to_records(index=False)

    # Convert each record to a tuple and return as a list
    return [tuple(record) for record in unique_records]

@app.post("/extract/uploaddocument/")
async def uploaddocument(applno: str,files: List[UploadFile] = File(...)):
    try:
        inserted_ids = []
        already_present_files = []
        for file in files:
            name = file.filename.split('.')[0]
            ext = file.filename.split('.')[-1]
            if ext.lower() != 'pdf' and ext.lower() != 'xml':
                already_present_files.append({"file_name": name, "error": "Document format is not supported"})
                continue

            file_path = f'{UPLOAD_FOLDER}/{name}.{ext}'
            with open(file_path, 'wb+') as f:
                f.write(file.file.read())

            check_data_present = get_loadedfiles_data(conn,file_path,applno)
            if check_data_present is not None :
                already_present_files.append({"file_name": name, "error": f"This file with docid {check_data_present.get('docid')} for applno '{check_data_present.get('applno')}' already present in the DB"})
                continue
            inserted_id = insert_loadedfiles_path(conn,applno,file_path)
            inserted_ids.append({"id": inserted_id, "file_path": file_path})

        if already_present_files:
            message = "Some files encountered errors:"
            for error_file in already_present_files:
                message += f" Filename '{error_file['file_name']}': '{error_file['error']}'"
            return {
                "message": message,
                "inserted_ids": inserted_ids
            }

        message = "Documents and its applno are inserted in the loadedfiles table successfully"
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Document format is not supported")
    except Exception as e:
        message = f"Error In Uploading Documents and its applno: {str(e)}"
        raise HTTPException(status_code=500, detail=message)

    return {
        "message": message,
        "inserted_ids": [InsertedFile(**item) for item in inserted_ids]
    }

@app.post("/extract/extract_details/")
async def extract_details(docid: int):
    message = "Default message"
    get_id = get_key_value_id(conn,docid)
    if get_id == docid:
        raise HTTPException(status_code=200, detail="Details Already extracted and inserted into the DB")

    pdf_path = get_docname(conn,docid)
    if pdf_path is None or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    filename, file_extension = os.path.splitext(pdf_path)
    if file_extension.lower() == '.xml':
        return {"pdf_path": pdf_path}
        
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
                # account_num = details['accountno']
            else:
                details = extract.extract_key_value_sbi(info)
                details['address'] = details['address'].replace("\n", " ")
                details['docid'] = docid
                details['bankname'] = bank
                # account_num = details['accountno']
            # check_data_present = get_key_value_data(conn,account_num)
            # if check_data_present is not None and details.get('statementperiod') == check_data_present.get('statementperiod'):
            #     raise HTTPException(status_code=409, detail=f"Details for docid {check_data_present.get('docid')} already present in the DB")
            insert_details(conn,details)

        elif bank == "HDFC Bank":
            details = extract.extract_key_value_hdfc(info)
            details['bankaddress'] = details['bankaddress'].replace("\n", " ")
            details['odlimit'] = details['odlimit'].replace("\n", " ")
            details['docid'] = docid
            details['bankname'] = bank
            # account_num = details['accountno']
            # check_data_present = get_key_value_data(conn,account_num)
            # if check_data_present is not None and details.get('statementperiodfrom') == check_data_present.get('statementperiodfrom') and details.get('statementperiodto') == check_data_present.get('statementperiodto'):
            #     raise HTTPException(status_code=409, detail=f"Details for docid {check_data_present.get('docid')} already present in the DB")
            insert_details(conn,details)

        elif bank == "INDIAN BANK":
            details = extract.extract_key_value_indian(info)
            details['address'] = ', '.join(details['address'])
            details['docid'] = docid
            details['bankname'] = bank
            # account_num = details['accountno']
            # check_data_present = get_key_value_data(conn,account_num)
            # if check_data_present is not None and details.get('statementperiod') == check_data_present.get('statementperiod'):
            #     raise HTTPException(status_code=409, detail=f"Details for docid {check_data_present.get('docid')} already present in the DB")
            insert_details(conn,details)

        elif bank == "UNION BANK OF INDIA":
            details = extract.extract_key_value_union(info)
            details['statementperiodto'] = details['statementperiodto'].replace("\n", "")
            details['docid'] = docid
            details['bankname'] = bank
            # account_num = details['accountno']
            # check_data_present = get_key_value_data(conn,account_num)
            # if check_data_present is not None and details.get('statementperiodfrom') == check_data_present.get('statementperiodfrom') and details.get('statementperiodto') == check_data_present.get('statementperiodto'):
            #     raise HTTPException(status_code=409, detail=f"Details for docid {check_data_present.get('docid')} already present in the DB")
            insert_details(conn,details)

        elif bank == "BANK OF BARODA":
            text_with_coords_bob = first_page.extract_table({"vertical_strategy": "text","horizontal_strategy": "text","min_words_vertical": 2})
            details = extract.extract_key_value_bob(text_with_coords_bob)
            details['docid'] = docid
            details['bankname'] = bank
            # account_num = details['accountno']
            # check_data_present = get_key_value_data(conn,account_num)
            # if check_data_present is not None and details.get('statementperiod') == check_data_present.get('statementperiod'):
            #     raise HTTPException(status_code=409, detail=f"Details for docid {check_data_present.get('docid')} already present in the DB")
            insert_details(conn,details)

        elif bank == "AXIS BANK":
            details = extract.extract_key_value_axis(info)
            details['address'] = details['address'].replace("\n", " ")
            details['docid'] = docid
            details['bankname'] = bank
            # account_num = details['accountno']
            # check_data_present = get_key_value_data(conn,account_num)
            # if check_data_present is not None and details.get('statementperiodfrom') == check_data_present.get('statementperiodfrom') and details.get('statementperiodto') == check_data_present.get('statementperiodto'):
            #     raise HTTPException(status_code=409, detail=f"Details for docid {check_data_present.get('docid')} already present in the DB")
            insert_details(conn,details)

        elif bank == "YES BANK":
            details = extract.extract_key_value_yes(info)
            details['docid'] = docid
            details['bankname'] = bank
            # account_num = details['accountno']
            # check_data_present = get_key_value_data(conn,account_num)
            # if check_data_present is not None and details.get('statementperiod') == check_data_present.get('statementperiod'):
            #     raise HTTPException(status_code=409, detail=f"Details for docid {check_data_present.get('docid')} already present in the DB")
            insert_details(conn,details)
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
    transaction_id = get_transaction_id(conn,docid)
    if transaction_id == docid:
        raise HTTPException(status_code=200, detail="Table Data Already parsed and inserted into the DB")

    # duplicate_insertion = get_key_value_id(conn,docid)
    # if duplicate_insertion is None:
    #     raise HTTPException(status_code=409, detail="Transaction data cannot be  parsed as Key_values are not parsed for this docid.")

    pdf_path = get_docname(conn,docid)
    if pdf_path is None or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    filename, file_extension = os.path.splitext(pdf_path)
    if file_extension.lower() == '.xml':
        return {"pdf_path": pdf_path}

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
        ids = loadedfiles_id(conn,applno)
        trans = get_transaction_data(conn,ids)
        if trans != []:
            trans = filter_unique_records(trans)
            months = expenditure.distinct_months(trans)
            expd = expenditure.classify_trans(trans)
            data = expenditure.money(expd)
            gross_income = expenditure.repeated_credits(data,months)
            expenses = expenditure.repeated_debits(data,months)
            emi = get_emi(conn,applno)
            update_loan_details(conn,applno,gross_income,expenses,emi)
            rating_calculation(conn,applno)
            delete_data_by_docid(conn,ids)
            message = "Rating calculated and updated in loanDetails table successfully"
        else:
            message = "No transactions data found for the application number"
    except Exception as e:
        message = f"Error In Calculating Rating engine: {str(e)}"

    return Rating(message=message)