import yaml
import streamlit as st
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities import LoginError
import pandas as pd
from datetime import datetime
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import time
import schedule
import os
from dotenv import load_dotenv
load_dotenv()
# Loading config file
with open('config.yaml', 'r', encoding='utf-8') as file:
    config = yaml.load(file, Loader=SafeLoader)

# Creating the authenticator object
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
)

EXCEL_FILE_PATH = 'expenses.xlsx'
def send_email(subject, body, to_email):
    # Replace with your Brevo API key
    BREVO_API_KEY = os.getenv("BREVO_API_KEY")
    
    # Configure API key authorization
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY

    # Create an instance of the API class
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    # Create the email
    sender = {"name": "Credit Card Monitor", "email": "meetpatelcompany@gmail.com"}  # Sender details
    receiver = [{"email": to_email}]  # Recipient details
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=receiver,
        html_content=body,
        sender=sender,
        subject=subject
    )
    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        st.success("Email sent successfully!")
    except ApiException as e:
        st.error(f"Failed to send email: {e}")

def generate_email_body(expenses):
    total_expense = expenses['Amount'].sum()
    html = f"""
    <h2>Daily Expense Report</h2>
    <h3>Total Expense: <strong>${total_expense:.2f}</strong></h3>
    <h3>Expense Details:</h3>
    {expenses.to_html(index=False)}
    """
    return html


# def send_daily_email():
#     to_email = "meetpatel8122001@gmail.com"
#     subject = "Credit Card Expense Report"
#     body = generate_email_body(load_data())
#     send_email(subject, body, to_email)

def load_data():
    try:
        df = pd.read_excel(EXCEL_FILE_PATH)
        # Convert 'Date' column to string
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
        return df
    except FileNotFoundError:
        # Initialize DataFrame with columns if the file does not exist
        return pd.DataFrame(columns=['Date', 'Expense Name', 'Amount'])

def save_data(df):
    # Convert 'Date' column to datetime before saving
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df.to_excel(EXCEL_FILE_PATH, index=False)

# Creating a login widget
try:
    authenticator.login()
except LoginError as e:
    st.error(e)

if st.session_state["authentication_status"]:
    
    st.write(f'Welcome *{st.session_state["name"]}*')
    st.sidebar.header('Add/Edit Expense')

    date = st.sidebar.date_input('Date')
    expense_name = st.sidebar.text_input('Expense Name')
    amount = st.sidebar.number_input('Amount', min_value=0.0, format="%.2f")

    # Handling form submission
    if st.sidebar.button('Submit'):
        new_row = pd.DataFrame({
            'Date': [date],
            'Expense Name': [expense_name],
            'Amount': [amount]
        })

        df = load_data()  # Reload data from Excel

        # Add new row to DataFrame
        df = pd.concat([df, new_row], ignore_index=True)

        # Save DataFrame to Excel
        save_data(df)

    # Display existing entries with edit options
    st.title('Credit Card Expenses Dashboard')

    df = load_data()  # Reload data from Excel

    # Display the total expense
    total_expense = df['Amount'].sum()
    st.write(f'### Total Expense: ${total_expense:.2f}')

    # Editing selected entry
    st.sidebar.header('Edit Expense')

    # Select an entry to edit
    edit_index = st.sidebar.selectbox('Select Expense to Edit', options=df.index, format_func=lambda x: f"{df.loc[x, 'Expense Name']} - {df.loc[x, 'Amount']}")

    if edit_index is not None:
        # Find the row to edit
        edit_row = df.loc[edit_index]
        
        st.sidebar.write(f"Editing Expense: {edit_row['Expense Name']}")

        # Pre-fill the sidebar inputs with the existing data
        date = st.sidebar.date_input('Date', value=pd.to_datetime(edit_row['Date']), key='edit_date')
        expense_name = st.sidebar.text_input('Expense Name', value=edit_row['Expense Name'], key='edit_expense_name')
        amount = st.sidebar.number_input('Amount', min_value=0.0, format="%.2f", value=float(edit_row['Amount']), key='edit_amount')

        if st.sidebar.button('Update'):
            updated_row = pd.DataFrame({
                'Date': [date],
                'Expense Name': [expense_name],
                'Amount': [amount]
            })

            df = load_data()  # Reload data from Excel
            # Update the row
            df.loc[edit_index] = updated_row.iloc[0]

            # Save DataFrame to Excel
            save_data(df)

    # Display the DataFrame
    st.write('### Expenses DataFrame')
    st.dataframe(df)

    # Delete selected entry
    st.sidebar.header('Delete Expense')

    # Select an entry to delete
    delete_index = st.sidebar.selectbox('Select Expense to Delete', options=df.index, format_func=lambda x: f"{df.loc[x, 'Expense Name']} - {df.loc[x, 'Amount']}")

    if st.sidebar.button('Delete'):
        df = load_data()  # Reload data from Excel
        df = df.drop(delete_index)
        save_data(df)
        st.rerun()  # Use st.rerun() instead of st.experimental_rerun()

    st.subheader("Email Settings")
    to_email = st.text_input("Enter your email to receive test reports")
    if st.button("Send Test Email"):
        if to_email:
            subject = "Test Expense Report"
            body = generate_email_body(load_data())
            send_email(subject, body, to_email)
        else:
            st.error("Please enter a valid email address.")
        
    authenticator.logout()
    # schedule.every().day.at("02:45").do(send_daily_email)
    # send_daily_email()
    while True:
        # send_daily_email()
        # schedule.run_pending()
        time.sleep(1)

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')

# Saving config file
with open('config.yaml', 'w', encoding='utf-8') as file:
    yaml.dump(config, file, default_flow_style=False)