import pdfplumber
import pandas as pd

class ExtractTable:
    def __init__(self):pass

    def extract_table_sbi(self,path):
        with pdfplumber.open(path) as pdf:
            all_tables = []
            for page in pdf.pages:
                tables = page.extract_table()
                if tables:
                    all_tables.extend(tables)
        return all_tables

    def extract_table_indian(self,path):
        with pdfplumber.open(path) as pdf:
            all_tables = []
            for page in pdf.pages:
                tables = page.extract_table()
                if tables:
                    all_tables.extend(tables)
        return all_tables

    def extract_table_union(self,path):
        with pdfplumber.open(path) as pdf:
            all_tables = []
            for page in pdf.pages:
                tables = page.extract_table()
                if tables:
                    all_tables.extend(tables)
        return all_tables

    def extract_table_axis(self,path):
        with pdfplumber.open(path) as pdf:
            all_tables = []
            for page in pdf.pages:
                tables = page.extract_table()
                if tables:
                    all_tables.extend(tables)
        return all_tables

    def extract_table_yes(self,path):
        with pdfplumber.open(path) as pdf:
            all_tables = []
            for page in pdf.pages:
                # table_settings_BOB = {"vertical_strategy": "text","horizontal_strategy": "lines","snap_tolerance": 7,"min_words_vertical": 4,"snap_x_tolerance": 7,"snap_y_tolerance": 7,"join_tolerance": 7,"join_x_tolerance": 7,"join_y_tolerance": 7}
                table_settings_BOB = {"vertical_strategy": "text","horizontal_strategy": "lines",
                "snap_tolerance": 7,"min_words_vertical": 12,"snap_x_tolerance": 7,"snap_y_tolerance": 7,"join_tolerance": 7,
                "join_x_tolerance": 7,"join_y_tolerance": 7}
                tables = page.extract_table(table_settings_BOB)
                if tables:
                    all_tables.extend(tables)
        return all_tables

    def extract_table_bob(self,path):
        with pdfplumber.open(path) as pdf:
            all_tables = []
            for page in pdf.pages:
                # table_settings_BOB = {"vertical_strategy": "text","horizontal_strategy": "lines","snap_tolerance": 7,"min_words_vertical": 4,"snap_x_tolerance": 7,"snap_y_tolerance": 7,"join_tolerance": 7,"join_x_tolerance": 7,"join_y_tolerance": 7}
                table_settings_BOB = {"vertical_strategy": "text","horizontal_strategy": "lines",
                "snap_tolerance": 7,"min_words_vertical": 8,"edge_min_length":8,"snap_x_tolerance": 7,"snap_y_tolerance": 7,"join_tolerance": 7,
                "join_x_tolerance": 7,"join_y_tolerance": 7}
                tables = page.extract_table(table_settings_BOB)
                if tables:
                    all_tables.extend(tables)
        return all_tables

    def extract_table_details_hdfc(self,data,page):
        expanded_df = pd.DataFrame()
        if page.page_number == 1:
            columns = ['Txn_Date','Description','ChequeNumber','Value_Date','Debit','Credit','Balance']
            df = pd.DataFrame(data[1:], columns=columns)
            for column in df.columns:
                df[column] = df[column].str.split('\n')
            
            expanded_rows = []
            for i, row in df.iterrows():
                row_data = row.tolist()
                max_len = max(len(val) for val in row_data if val is not None)
                for j in range(max_len):
                    new_row = [row_data[col][j] if row_data[col] is not None and len(row_data[col]) > j else '' for col in range(len(row_data))]
                    # new_row = [row_data[col][j] if len(row_data[col]) > j else '' for col in range(len(row_data))]
                    expanded_rows.append(new_row)
            expanded_df = pd.DataFrame(expanded_rows, columns=df.columns)
        else:
            # columns = ['Date','Narration','Chq./Ref.No.','ValueDt','WithdrawalAmt.','DepositAmt.','ClosingBalance']
            columns = ['Txn_Date','Description','ChequeNumber','Value_Date','Debit','Credit','Balance']
            df = pd.DataFrame(data[0:], columns=columns)
            for column in df.columns:
                df[column] = df[column].str.split('\n')
                
            expanded_rows = []
            for i, row in df.iterrows():
                row_data = row.tolist()
                max_len = max(len(val) for val in row_data if val is not None)
                for j in range(max_len):
                    new_row = [row_data[col][j] if row_data[col] is not None and len(row_data[col]) > j else '' for col in range(len(row_data))]
                    # new_row = [row_data[col][j] if len(row_data[col]) > j else '' for col in range(len(row_data))]
                    expanded_rows.append(new_row)
            expanded_df = pd.DataFrame(expanded_rows, columns=df.columns)
        return expanded_df

    def extract_table_hdfc(self,path):
        with pdfplumber.open(path) as pdf:
            dfs_list = []
            for page in pdf.pages:
                table_settings_hdfc = {"vertical_strategy": "lines","horizontal_strategy": "text","explicit_vertical_lines": [],"explicit_horizontal_lines": [],"snap_tolerance": 7,"snap_x_tolerance": 7,"snap_y_tolerance": 7,"join_tolerance": 7,"join_x_tolerance": 7,"join_y_tolerance": 7}
                tables = page.extract_table(table_settings_hdfc)
                deatils_table =self.extract_table_details_hdfc(tables,page)
                dfs_list.append(deatils_table)
            concatenated_df = pd.concat(dfs_list)
            concatenated_df['Txn_Date'] = pd.to_datetime(concatenated_df['Txn_Date'].str.strip(), format='%d/%m/%y', errors='coerce')
            concatenated_df = concatenated_df[concatenated_df['Txn_Date'].notnull()]
        return concatenated_df