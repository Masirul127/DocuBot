import re

class Extraction:
    def __init__(self):pass

    def get_ifsc(self,text):
        ifsc_category = ['IFSC','IFS Code','RTGS/NEFTIFSC']
        for val in ifsc_category:
            ifsc = text.find(val)
            if ifsc != -1:
                new_text = text[ifsc : ifsc + 37]
                ifsc_code = re.findall(r'[A-Z0-9]{11}', new_text)
                if ifsc_code :
                    return ifsc_code
                else:
                    return None

    def classify_bank(self,text):
        '''
        Takes OCR text from first page and detects IFSC code, to infer the bank by using it
        '''
        banks = {"YES": "YES BANK", "ALLA": "ALLAHABAD BANK","SBI":"STATE BANK OF INDIA","BARB":"BANK OF BARODA","UTIB":"AXIS BANK","UBIN":"UNION BANK OF INDIA","HDFC":"HDFC Bank"}
        ifsc = self.get_ifsc(text)
        if ifsc:
            matches = [word for word in ifsc if re.match(r'[A-Za-z][A-Za-z0-9_]*', word)][0]
            # code =re.findall(r'[A-Za-z][A-Za-z0-9_]*', ifsc)
            bank = ""
            for j in banks.keys():
                if j in matches:
                    bank = banks[j]
                    break
        else:
            return("Ifsc code not found")
        return bank

    def extract_key_value_sbi(self,text):
        details = {}
        cleaned_text = text.replace('(cid:9)', '')
        #Extracting Account Number
        account_number = re.search(r'Account Number :\s*(\d+)', cleaned_text)
        details['accountno'] = account_number.group(1) if account_number else "Not Found"
        #Extracting Account Name
        account_name = re.search(r'Account Name :(.*?)\n', cleaned_text)
        details['accountholder'] = account_name.group(1) if account_name else "Not Found"
        #Extracting Address
        address = re.search(r'Address\s+:\s+(.*?)\nDate', cleaned_text, re.DOTALL)
        details['address'] = address.group(1) if address else "Not Found"
        #Extracting Balance as on
        balance_as_on = re.search(r'Balance as on (\d+ \w+ \d+)', cleaned_text)
        details['balanceason'] = balance_as_on.group(1) if balance_as_on else "Not Found"
        #Extracting account statement date
        account_statement = re.search(r'Account Statement from \d+ \w+ \d+ to \d+ \w+ \d+', cleaned_text)
        details['statementperiod'] = account_statement.group(0) if account_statement else "Not Found"
        balanceamount = re.search(r"Balance as on (\d{1,2} \w{3} \d{4}) :[\n\s]*([\d,.]+)", cleaned_text)
        details['balanceamount'] = balanceamount.group(2) if balanceamount else "Not Found"
        # Extract other details using regex patterns and keys
        patterns = {
            'date': r'Date\s*:\s*([^\n]+)\n',
            'accountdescription': r'Account Description\s*:\s*([^\n]+)\n',
            'branch': r'Branch\s*:\s*([^\n]+)\n',
            'drawingpower': r'Drawing Power\s*:\s*([^\n]+)\n',
            'interestrate': r'Interest Rate\(% p\.a.\) :\s*([0-9.]+)',
            'modbalance': r'MOD Balance\s*:\s*([^\n]+)\n',
            'cif': r'CIF No\.\s*:\s*([^\n]+)\n',
            'ifsc': r'IFS Code\s*:\s*([^\n]+)\n\(Indian Financial System\)\n',
            'micrcode': r'MICR Code\s*:\s*([^\n]+)\n\(Magnetic Ink Character Recognition\)\n',
            'nominationregistered': r'Nomination Registered\s*:\s*([^\n]+)\n'
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, cleaned_text)
            details[key] = match.group(1) if match else "Not Found"

        return details

    def extract_key_value_sbi_yono(self,text):
        details = {}
        patterns = {
            "accountholder": r"Account Name (\w+\s\w+)",
            "address": r"Address (.+)",
            "date": r"Date (\d+\s\w+\s\d{4})",
            "accountno": r"Account Number (\d+)",
            "accountdescription": r"Account Description (\w+)",
            "branch": r"Branch (.+)",
            "drawingpower": r"Drawing Power (\d+\.\d+)",
            "interestrate": r"Interest Rate\(%p\.a\.\) (\d+\.\d+)",
            "cif": r"CIF No\. (\d+)",
            "ifsc": r"IFS Code (\w+)",
            "micrcode": r"MICR Code (\d+)",
            "nominationregistered": r"Nomination Registered (\w+)",
            "balanceason": r"Balance as on (\d+\s\w+\s\d{4})",
            "balanceamount": r"Balance as on \d+\s\w+\s\d{4} (INR \d+\.\d+)",
            "statementperiod": r"Search for (.+)"
        }

        # Extract information using regex
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            details[key] = match.group(1) if match else "Not Found"
        return details

    def extract_key_value_indian(self,text):
        details = {}
        pattern = r'Product type :\s*(.*?)\n(?=Email)'
        match = re.search(pattern, text, re.DOTALL)
        data_between_product_and_email = match.group(1).strip().split('\n')
        details['accountholder'] = data_between_product_and_email[1]
        details['address'] = data_between_product_and_email[2:5]
        branchname_address = re.search(r'Page No: (\d+)\n(.*?)\nBranch Code', text,re.DOTALL)
        branchname_address_match = branchname_address.group(2).strip().split('\n')
        details['branch'] = branchname_address_match[1]
        details['bankaddress'] = branchname_address_match[2]
        statementfrom = re.search(r'STATEMENT OF ACCOUNT from (.*?) for Account Number', text,re.DOTALL)
        details['statementperiod'] = statementfrom.group(1) if statementfrom else "Not Found"
        patterns = {
            'branchcode': r'Branch Code\s*:\s*(\d+)',
            'accountno': r'Account Number\s*:\s*(\d+)',
            'producttype': r'Product type\s*:\s*(\S+)',
            'email': r'Email\s*:\s*([\w\.-]+@[\w\.-]+)',
            'statementdate': r'Statement Date :(.+?)\nCleared Balance',
            'clearedbalance': r'Cleared Balance\s*:\s*(\d+\.\d+)',
            'unclearedamount': r'Uncleared Amount\s*:\s*(\d+\.\d+)',
            'drawingpower': r'Drawing Power\s*:\s*(\d+\.\d+)',
            'interestrate': r'Interest Rate\s*:\s*(\d+\.\d+)'
        }

        # Extract information using regex
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            details[key] = match.group(1) if match else "Not Found"
        return details

    def extract_key_value_hdfc(self,text):
        details = {}
        account_number = re.search(r'AccountNo\s*:\s*(\d+)', text)
        details['accountno'] = account_number.group(1) if account_number else "Not Found"
        bankaddress_match = re.search(r'Address\s*:\s*([^:]+)\s*City', text)
        details['bankaddress'] = bankaddress_match.group(1) if bankaddress_match else "Not Found"
        name_match = re.search(r'\b(MR|MR.|MRS|MS|SHRI)\.? (\S+)', text)
        details['accountholder'] = name_match.group(0) if name_match else "Not Found"
        address_match = re.search(r'State\s*:\s*([^\n]+)\n([^\n]+)\s*Phoneno\.', text)
        details['address'] = address_match.group(2) if address_match else "Not Found"
        address_match1 = re.search(r'(.*)(?=ODLimit)', text)
        details['address1'] = address_match1.group(1) if address_match1 else "Not Found"
        address_match2 = re.search(r'Currency\s*:\s*([^\n]+)\n([^\n]+)\s*Email', text)
        details['address2'] = address_match2.group(2) if address_match2 else "Not Found"
        address_match3 =re.search(r'(.*)(?=CustID)', text)
        details['address3'] = address_match3.group(1) if address_match3 else "Not Found"
        address_match4 =re.search(r'(.*)(?=AccountNo)', text)
        details['address4'] = address_match4.group(1) if address_match4 else "Not Found"
        jointholders =re.search(r'(.*?)\s*AccountStatus', text)
        details['jointholders'] = jointholders.group(1) if jointholders else "Not Found"
        odlimit =re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*)Currency\s*:', text)
        details['odlimit'] = odlimit.group(1) if odlimit else "Not Found"

        # Extract other details using regex patterns and keys
        patterns = {
            'branch': r'AccountBranch\s*:\s*([^\n\r]+)',
            'city': r'City\s*:\s*([^\n\r]+)',
            'state': r'State\s*:\s*([^\n\r]+)',
            'phone': r'Phoneno\.\s*:\s*([\d-]+)',
            'currency': r'Currency\s*:\s*(\S.*)',
            'email': r'Email\s*:\s*([^\n\r]+)',
            'cif': r'CustID\s*:\s*(\d+)',
            'opendate': r'A/COpenDate\s*:\s*([\d/]+)',
            'accountstatus': r'AccountStatus\s*:\s*([^\n\r]+)',
            'ifsc': r'RTGS/NEFTIFSC\s*:\s*([^\n\r:\s]+)',
            'micrcode': r'MICR\s*:\s*([\d]+)',
            'branchcode': r'BranchCode\s*:\s*([\d]+)',
            'productcode': r'ProductCode\s*:\s*([\d]+)',
            'nomination': r'Nomination\s*:\s*([^\n\r]+)',
            'statementperiodfrom': r'From\s*:\s*([\d/]+)',
            'statementperiodto': r'To\s*:\s*([\d/]+)'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            details[key] = match.group(1) if match else "Not Found"

        return details

    def extract_key_value_union(self,text):
        details = {}
        address1_match = re.search(r'Customer/CIF ID (\d+)\n(.*?)(?=\nAddress)', text)
        details['address'] = address1_match.group(2) if address1_match else "Not Found"
        address2_match = re.search(r'(?<=Address )(.*?)(?=Account)', text)
        details['address1'] = address2_match.group(1) if address2_match else "Not Found"
        address3_match = re.search(r'(.*?)\nAccount Number', text)
        details['address2'] = address3_match.group(1) if address3_match else "Not Found"
        branchadd_match = re.search(r'Branch Address (.*?)\nPincode', text)
        details['bankaddress'] = branchadd_match.group(1) if branchadd_match else "Not Found"
        branchadd1_match = re.search(r'(.*?)\nMobile No', text)
        details['bankaddress1'] = branchadd1_match.group(1) if branchadd1_match else "Not Found"

        patterns = {
        "accountholder": r"Name\s*(\w+\s*\w+)",
        "accountno": r"Account\s*Number\s*(\d+)", 
        "cif": r"Customer/CIF\s*ID\s*(\d+)",
        "accounttype": r"Account\s*Type\s*([^J]+)",
        "ifsc": r'\bIFSC\b\s([A-Z]{4}\d{7})',
        'email': r'Email\s*Id\s*(\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b)',
        "mobileno": r"Mobile\s*No\s*(\d+)",
        "pincode": r"Pincode\s*(\d+)",
        "city": r"City\s*(\w+\s*\s+)",
        "state": r"State\s*(\w+\s*\w+)",
        "branch": r"Home\s*branch\s*(\w+\s*\s+)",
        "currency": r"Currency\s*(\w+\s*\s+)",
        "statementdate": r"Statement\s*Date\s*(\b\d{2}/\d{2}/\d{4} \d{2}:\d{2} (?:AM|PM)\b)",
        "statementperiodfrom": r"Statement\s*Period\s*([\d/]+)",
        "statementperiodto": r'To\s*([\d\n/]+)'
        }

        # Extract key-value pairs using regular expressions
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                details[key] = match.group(1).strip()
        return details

    def extract_values(self,data_list):
        details = {}
        index_customerName_Branchname = data_list.index('Customer Name                                        Branch Name')
        customerName_Branchname_Value = data_list[index_customerName_Branchname + 1]
        parts = customerName_Branchname_Value.split("                                ")
        details['accountholder'] = parts[0]
        details['branch'] = parts[1]
        index_AccountNumber_IFSC = data_list.index('AccountNumber                                        IFSC Code')
        AccountNumber_IFSC_Value = data_list[index_AccountNumber_IFSC + 1]
        parts1 = AccountNumber_IFSC_Value.split("                                        ")
        details['accountno'] = parts1[0]
        details['ifsc'] = parts1[1]
        index_AccountType_MICR = data_list.index('AccountType                                        MICR Code')
        AccountType_MICR_Value = data_list[index_AccountType_MICR + 1]
        parts3 = AccountType_MICR_Value.split("                                            ")
        details['accounttype'] = parts3[0]
        details['micrcode'] = parts3[1]
        # index_AccountFrom_To = data_list.index('        Account Statement from 01-04-2023 to    30-06-2023    ')
        AccountFrom_To_Value = data_list[0]
        details['statementperiod'] = AccountFrom_To_Value
        index_customerAdd_BranchAdd = data_list.index('Customer Address                                        Branch Address')
        customerAdd_BranchAdd_Value1 = data_list[index_customerAdd_BranchAdd + 1]
        parts4 = customerAdd_BranchAdd_Value1.split("        ")
        details['address'] = parts4[0]
        details['bankaddress'] = parts4[1]
        customerAdd_BranchAdd_Value2 = data_list[index_customerAdd_BranchAdd + 2]
        parts5 = customerAdd_BranchAdd_Value2.split("            ")
        details['address1'] = parts5[0]
        details['bankaddress1'] = parts5[2]
        customerAdd_BranchAdd_Value3 = data_list[index_customerAdd_BranchAdd + 3]
        parts6 = customerAdd_BranchAdd_Value3.split("            ")
        details['address2'] = parts6[0]
        details['bankaddress2'] = parts6[2]
        customerAdd_BranchAdd_Value4 = data_list[index_customerAdd_BranchAdd + 4]
        parts7 = customerAdd_BranchAdd_Value4.split("            ")
        details['address3'] = parts7[0]
        details['bankaddress3'] = parts7[1]
        
        return details

    def get_index_and_result(self,stored_results):
        result_list = []
        for result in stored_results:
            if result != '                                                    ':
                result_list.append(result)
        return result_list

    def extract_key_value_bob(self,data):
        processed_data = [''.join(word + ' ' * (4 if word == '' else 0) for word in row) for row in data]
        stored_results = processed_data
        index_result_pairs = self.get_index_and_result(stored_results)
        value = self.extract_values(index_result_pairs)
        return value

    def extract_key_value_axis(self,data):
        details = {}
        customer_id = re.search(r'Customer ID\s*:\s*(\d+)', data)
        details['cif'] = customer_id.group(1) if customer_id else "Not Found"
        ifsc_code = re.search(r'IFSC Code\s*:\s*([A-Z0-9]+)', data)
        details['ifsc'] = ifsc_code.group(1) if ifsc_code else "Not Found"
        mobile_no = re.search(r'Registered Mobile No\s*:\s*XXXXXX(\d{4})', data)
        details['mobileno'] = 'XXXXXX' + mobile_no.group(1) if mobile_no else "Not Found"
        # actual_mobile = 'XXXXXX' + mobile_no.group(1)
        email = re.search(r'Registered Email ID\s*:\s*([A-Za-z0-9_.]+@[A-Za-z0-9]+\.[A-Za-z0-9_.]+)', data)
        details['email'] = email.group(1) if email else "Not Found"
        pan = re.search(r'PAN\s*:\s*([A-Z0-9]+)', data)
        details['pan'] = pan.group(1) if pan else "Not Found"
        scheme = re.search(r'Scheme\s*:\s*(.+)', data)
        details['scheme'] = scheme.group(1) if scheme else "Not Found"
        account_no = re.search(r'Account No\s*:\s*(\d+)', data)
        details['accountno'] = account_no.group(1) if account_no else "Not Found"
        micr_code = re.search(r'MICR Code\s*:\s*(\d+)', data)
        details['micrcode'] = micr_code.group(1) if micr_code else "Not Found"
        nominee_registered = re.search(r'Nominee Registered\s*:\s*(Y|N)', data)
        details['nominationregistered'] = nominee_registered.group(1) if nominee_registered else "Not Found"
        # is_registered = nominee_registered.group(1)
        dates = re.search(r'From : (\d{2}-\d{2}-\d{4}) To : (\d{2}-\d{2}-\d{4})', data)
        details['statementperiodfrom'] = dates.group(1) if dates else "Not Found"
        details['statementperiodto'] = dates.group(2) if dates else "Not Found"
        name = re.search(r'(.+?)\nJoint Holder', data)
        details['accountholder'] = name.group(1) if name else "Not Found"
        joint_holder = re.search(r'Joint Holder :- (.+)', data)
        details['jointholder'] = joint_holder.group(1) if joint_holder else "Not Found"
        address_match = re.search(r'Joint Holder :- -\n(.*?)Customer ID', data, re.DOTALL)
        details['address'] = address_match.group(1) if address_match else "Not Found"
        address1_match = re.search(r'Customer ID :(\d+)\n(.*?)IFSC Code', data, re.DOTALL)
        details['address1'] = address1_match.group(2) if address1_match else "Not Found"
        address2_match = re.search(r'IFSC Code :(\w+)\n(.*?)MICR Code', data, re.DOTALL)
        details['address2'] = address2_match.group(2) if address2_match else "Not Found"
        return details

    def extract_key_value_yes(self,text):
        details = {}
        pattern = r'Address:(.*?)\nIFSC'
        match = re.search(pattern, text, re.DOTALL)
        data_between_product_and_email = match.group(1).strip().split('\n')
        details['bankaddress1'] = data_between_product_and_email[2]
        details['address2'] = data_between_product_and_email[1]
        details['address3'] = data_between_product_and_email[3]

        pattern1 = r'MICR:(.*?)\nCustId'
        match = re.search(pattern1, text, re.DOTALL)
        data_after_MICR = match.group(1).strip().split('\n')
        details['address4'] = data_after_MICR[1]
        details['email'] = data_after_MICR[2]
        patterns = {
        "accountholder": r'\n(.*?)YourBranchDetails:',
        "accountno": r'ACCOUNTNo\.(\d+)', 
        "cif": r'CustId:(\d+)',
        "micrcode": r'MICR:(\d+)',
        "ifsc": r'IFSC:([A-Z0-9]+)',
        "address": r'\n(.*?)Name:',
        "address1": r'\n(.*?)\nAddress:',
        "bankaddress": r'Address:(.*?)\n',
        "branch": r'Name:(.*?)\n',
        "currency": r'Currency:([A-Z]+)',
        "statementperiod": r'Period:(.*?)\n'
        }

        # Extract key-value pairs using regular expressions
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                details[key] = match.group(1).strip()
        return details