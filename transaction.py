import pandas as pd

class Transaction:
    def __init__(self) -> None:
        pass

    def classify_trans(self,df):
        columns =['id','docid','SerialNo','TransactionId','Txn_Date','Value_Date','Description','ChequeNumber','Amount','Debit','Credit','Balance','Init.Br','bankname','RemitterBranch']
        df = pd.DataFrame(df,columns=columns)
        trans = df.to_dict(orient='records')
        '''
        Takes the transactions and classifies them into categories
        1. IMPS
        2. ATM
        3. FOOD
        4. SHOPPING
        5. CASH
        and others

        TODO: Make it less complicated and reusable
        '''
        # df = pd.read_excel("all_bank.xlsx")
        df = pd.DataFrame(trans)
        t = df["Description"]

        t = t.apply(lambda x: x.lower())

        # Removing numbers and special characters
        text = t.replace(to_replace="[0-9]", value="", regex=True).apply(
            lambda x: x.replace("/", "").replace("\\", "").replace(":", "").replace("\n", " ").replace("-", " ")
            .replace("/", " "))

        # Removing extra spaces created due to the above step
        for i in range(len(text)):
            x = text[i].split()
            for j in range(len(x)):
                x[j] = x[j].strip()
            text[i] = " ".join(x)

        #### TODO: Rewriting the dictionary in a better implementation

        labels = {"mpokk":"loan","krazyb":"loan","kreditb":"loan","loani": "loan","rent":"rent","imps": "imps", 
                "rrn": "imps", "loan": "loan","emi": "emi", "amazon": "shopping", "flipkart": "shopping",
                "mutualfund": "invest", "txn paytm": "trf", "restaurant": "food", "paytm": "trf",
                "atd": "atm", "atm": "atm", "net txn": "nettxn", "cash": "cash", "funds trf": "trf", "neft": "neft",
                "interest": "interest",
                "metro": "travel", "swiggy": "food", "faasos": "food", "zomato": "food", "upi": "trf", "ola": "travel",
                "refund": "refund",
                "charge": "bank_charges", "pca": "trf","salary":"salary"
                }

        labs = []

        # Labelling the transaction according to the dictionary defined
        for i in text:
            f = 0
            for j in list(labels.keys()):
                if j in i:
                    labs.append(labels[j])
                    f = 1
                    break
            if f == 0:
                labs.append("miscellaneous")
        df["Label"] = pd.DataFrame(labs)
        # x = df.Description.apply(lambda x: re.findall(r'[\w\.-]+@[\w\.-]+', x))
        # df["Remark"] = pd.DataFrame(x)
        return (df)

    def money(self,df):
        # df = pd.DataFrame(df)
        '''
        Creates a column for depicting the Credit and Debit numerically
        '''
        money = []
        type = []
        # df.index = df.index + 2
        df['Debit'] = df['Debit'].apply(lambda x: pd.to_numeric(x.replace(',', ''), errors='coerce'))
        df['Credit'] = df['Credit'].apply(lambda x: pd.to_numeric(x.replace(',', ''), errors='coerce'))
        for i in df.index:
            if df["Debit"][i] >0:
                money.append(-df["Debit"][i])
                type.append("Debit")
            else:
                    money.append(df["Credit"][i])
                    type.append("Credit")

        return (pd.concat([df, pd.DataFrame(money, columns=["flow"]), pd.DataFrame(type, columns=["type"])], axis=1))

    def distinct_months(self,df):
        columns =['id','docid','SerialNo','TransactionId','Txn_Date','Value_Date','Description','ChequeNumber','Amount','Debit','Credit','Balance','Init.Br','bankname','RemitterBranch']
        df = pd.DataFrame(df,columns=columns)
        trans = df.to_dict(orient='records')
        df = pd.DataFrame(trans)
        start_date = df['Txn_Date'].min()
        end_date = df['Txn_Date'].max()
        num_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
        return num_months

    def repeated_debits(self, df, months):
        # Convert 'Txn_Date' to datetime if it's not already
        df['Txn_Date'] = pd.to_datetime(df['Txn_Date'])
        
        # Group by month and debit amount
        df['Month'] = df['Txn_Date'].dt.to_period('M')
        grouped_df = df.groupby(['Month', 'Debit']).agg({'Txn_Date': list, 'Label': list}).reset_index()
        
        if months == 1:
            # Filter debits that are repeated at least `months` times
            repeated_debits = df['Debit'].value_counts()[df['Debit'].value_counts() >= 1].index
            repeated_df = df[df['Debit'].isin(repeated_debits)]

            # Filter debits that are repeated less than `months` times
            repeated_debits1 = df['Debit'].value_counts()[df['Debit'].value_counts() <= months].index
            repeated_df1 = df[df['Debit'].isin(repeated_debits1)]
        else:
            # Filter debits that are repeated at least `months` times
            repeated_debits = df['Debit'].value_counts()[df['Debit'].value_counts() > 1].index
            repeated_df = df[df['Debit'].isin(repeated_debits)]

            # Filter debits that are repeated less than `months` times
            repeated_debits1 = df['Debit'].value_counts()[df['Debit'].value_counts() < months].index
            repeated_df1 = df[df['Debit'].isin(repeated_debits1)]
        
        # Filter debits above 2000 and its label != 'loan' for each month
        high_debits_not_loan = repeated_df[(repeated_df['Debit'] > 2000) & (repeated_df['Label'] != 'loan')]
        grouped_high_debits_not_loan = high_debits_not_loan.groupby(['Month', 'Debit']).agg({'Txn_Date': list, 'Label': list}).reset_index()

        # Filter debits < 2000 and label != 'loan' for each month
        low_debits_not_loan = repeated_df1[(repeated_df1['Debit'] < 2000) & (repeated_df1['Label'] != 'loan')]
        grouped_low_debits_not_loan = low_debits_not_loan.groupby(['Month', 'Debit']).agg({'Txn_Date': list, 'Label': list}).reset_index()
        
        # Filter debits with label 'loan' for each month
        loan_debits = repeated_df[repeated_df['Label'] == 'loan']
        grouped_loan_debits = loan_debits.groupby(['Month', 'Debit']).agg({'Txn_Date': list, 'Label': list}).reset_index()

        discretionary_exp_monthwise = grouped_low_debits_not_loan.groupby('Month')['Debit'].sum().reset_index()
        discretionary_expense_sum = grouped_low_debits_not_loan['Debit'].sum()
        discretionary_expense = discretionary_expense_sum *(-0.5)

        merged_df = pd.concat([grouped_loan_debits, grouped_high_debits_not_loan])
        non_discretionary_exp_monthwise = merged_df.groupby('Month')['Debit'].sum().reset_index()
        non_discretionary_exp_sum = merged_df['Debit'].sum()
        non_discretionary_expenses = non_discretionary_exp_sum *(-1)

        total_expense_monthly = discretionary_expense + non_discretionary_expenses
        expenses = total_expense_monthly/months
        return expenses

    def repeated_credits(self, df, months):
        # Convert 'Txn_Date' to datetime if it's not already
        # df['Txn_Date'] = pd.to_datetime(df['Txn_Date'])
        
        # Group by month and credit amount
        df['Month'] = df['Txn_Date'].dt.to_period('M')
        grouped_df = df.groupby(['Month', 'Credit']).agg({'Txn_Date': list, 'Label': list}).reset_index()
        
        if months == 1:
            # Filter credits that are repeated at least `months` times
            repeated_credits = df['Credit'].value_counts()[df['Credit'].value_counts() >= 1].index
            repeated_df = df[df['Credit'].isin(repeated_credits)]

            # Filter credits that are repeated less than `months` times
            repeated_credits1 = df['Credit'].value_counts()[df['Credit'].value_counts() <= months].index
            repeated_df1 = df[df['Credit'].isin(repeated_credits1)]
        else:
            # Filter credits that are repeated at least `months` times
            repeated_credits = df['Credit'].value_counts()[df['Credit'].value_counts() > 1].index
            repeated_df = df[df['Credit'].isin(repeated_credits)]

            # Filter credits that are repeated less than `months` times
            repeated_credits1 = df['Credit'].value_counts()[df['Credit'].value_counts() < months].index
            repeated_df1 = df[df['Credit'].isin(repeated_credits1)]
        
        # Filter credits above 2000 and its label != 'loan' for each month
        high_credits = repeated_df[(repeated_df['Credit'] > 2000) & (repeated_df['Label'] != 'loan') & (repeated_df['Label'] != 'salary')]
        grouped_high_credits = high_credits.groupby(['Month', 'Credit']).agg({'Txn_Date': list, 'Label': list}).reset_index()

        # Filter credits < 2000 and label != 'loan' for each month
        interest_credit = repeated_df1[(repeated_df1['Credit'] < 2000) & (repeated_df1['Label'] == 'interest')]
        grouped_interest_credit = interest_credit.groupby(['Month', 'Credit']).agg({'Txn_Date': list, 'Label': list}).reset_index()
        
        # Filter debits with label 'salary' for each month
        salary_credits = repeated_df[repeated_df['Label'] == 'salary']
        grouped_salary_credits = salary_credits.groupby(['Month', 'Credit']).agg({'Txn_Date': list, 'Label': list}).reset_index()

        # Concatenate the three DataFrames
        merged_df = pd.concat([grouped_high_credits, grouped_salary_credits, grouped_interest_credit])

        # Calculate sum
        total_income_monthly = merged_df.groupby('Month')['Credit'].sum().reset_index()
        total_income= merged_df['Credit'].sum()
        gross_income = total_income/months
        return gross_income