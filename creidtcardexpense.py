import streamlit as st
import pandas as pd
from datetime import datetime
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import time
import schedule
import os
from dotenv import load_dotenv
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities import LoginError

# Load environment variables from .env file
load_dotenv()

# Load configuration for authentication
with open('config.yaml', 'r', encoding='utf-8') as file:
    config = yaml.load(file, Loader=SafeLoader)

# Path to the Excel file
EXCEL_FILE_PATH = 'expenses.xlsx'

# Function to load expenses from Excel
def load_expenses():
    try:
        df = pd.read_excel(EXCEL_FILE_PATH)
        # Ensure 'Date' column is in the correct format
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
        return df
    except FileNotFoundError:
        # If the file doesn't exist, create a new DataFrame
        return pd.DataFrame(columns=['Date', 'Expense Name', 'Amount'])

# Function to save expenses to Excel
def save_expenses(df):
    # Ensure 'Date' column is in the correct format before saving
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df.to_excel(EXCEL_FILE_PATH, index=False)

# Initialize session state for expenses
if 'expenses' not in st.session_state:
    st.session_state.expenses = load_expenses()

# Create the authenticator object
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
)

# Function to send email using Brevo
def send_email(subject, body, to_email):
    BREVO_API_KEY = os.getenv("BREVO_API_KEY")
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    sender = {"name": "Expense Tracker", "email": "meetpatelcompany@gmail.com"}
    receiver = [{"email": to_email}]
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=receiver,
        html_content=body,
        sender=sender,
        subject=subject
    )
    try:
        api_instance.send_transac_email(send_smtp_email)
        st.success("Email sent successfully!")
    except ApiException as e:
        st.error(f"Failed to send email: {e}")

# Function to generate the email body
def generate_email_body(expenses):
    total_expense = expenses['Amount'].sum()
    html = f"""
    <h2>Daily Expense Report</h2>
    <h3>Total Expense: <strong>${total_expense:.2f}</strong></h3>
    <h3>Expense Details:</h3>
    {expenses.to_html(index=False)}
    """
    return html

# Function to send daily email
def send_daily_email():
    to_email = "meetpatel8122001@gmail.com"
    subject = "Daily Expense Report"
    body = generate_email_body(st.session_state.expenses)
    send_email(subject, body, to_email)

# Schedule daily email at 8:00 AM


# send_daily_email()

# Login widget
try:
    authenticator.login()
except LoginError as e:
    st.error(e)

# Check authentication status
if st.session_state["authentication_status"]:
    st.write(f'Welcome *{st.session_state["name"]}*')
    authenticator.logout()

    # Sidebar for adding, editing, and removing expenses
    with st.sidebar:
        st.header("Add/Edit/Remove Expense")
        
        # Date input
        expense_date = st.date_input("Date", datetime.today())
        
        # Expense name input
        expense_name = st.text_input("Expense Name")
        
        # Amount input
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        
        # Add expense button
        if st.button("Add Expense"):
            new_expense = pd.DataFrame([[expense_date, expense_name, amount]], columns=['Date', 'Expense Name', 'Amount'])
            st.session_state.expenses = pd.concat([st.session_state.expenses, new_expense], ignore_index=True)
            save_expenses(st.session_state.expenses)  # Save to Excel
        
        # Edit expense
        st.subheader("Edit Expense")
        edit_index = st.number_input("Row Index to Edit", min_value=0, max_value=len(st.session_state.expenses)-1, value=0)
        if st.button("Edit Selected Expense"):
            st.session_state.expenses.at[edit_index, 'Date'] = expense_date
            st.session_state.expenses.at[edit_index, 'Expense Name'] = expense_name
            st.session_state.expenses.at[edit_index, 'Amount'] = amount
            save_expenses(st.session_state.expenses)  # Save to Excel
        
        # Remove expense
        st.subheader("Remove Expense")
        remove_index = st.number_input("Row Index to Remove", min_value=0, max_value=len(st.session_state.expenses)-1, value=0)
        if st.button("Remove Selected Expense"):
            st.session_state.expenses = st.session_state.expenses.drop(index=remove_index).reset_index(drop=True)
            save_expenses(st.session_state.expenses)  # Save to Excel

    # Main screen
    st.title("Expense Tracker")

    # Display total expense
    total_expense = st.session_state.expenses['Amount'].sum()
    st.metric("Total Expense", f"${total_expense:.2f}")

    # Display expenses in a table
    st.dataframe(st.session_state.expenses)

    # Download expenses as CSV
    st.download_button(
        label="Download Expenses as CSV",
        data=st.session_state.expenses.to_csv(index=False).encode('utf-8'),
        file_name='expenses.csv',
        mime='text/csv',
    )
    schedule.every().day.at("08:00").do(send_daily_email)
    
    # Run the scheduler in the background
    while True:
        schedule.run_pending()
        time.sleep(1)

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')

# Save configuration file
with open('config.yaml', 'w', encoding='utf-8') as file:
    yaml.dump(config, file, default_flow_style=False)