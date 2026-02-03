import os
from google_auth_oauthlib.flow import InstalledAppFlow

# The scope we need (Read and Send emails)
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)

    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

    print("Success! 'token.json' has been created.")

if __name__ == '__main__':
    main()