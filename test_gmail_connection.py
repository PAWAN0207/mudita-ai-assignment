
from integrations.gmail_client import (
    GmailConnectionError,
    list_recent_emails,
    test_gmail_connection,
)


def main():
    print("Checking Gmail connection...")

    try:
        account = test_gmail_connection()

        print("\nGMAIL CONNECTION SUCCESS")
        print("Account:", account["email"])
        print("Total messages:", account["messages_total"])
        print("Total threads:", account["threads_total"])

        print("\nReading recent inbox emails...")
        emails = list_recent_emails(max_results=5)

        print(f"Retrieved {len(emails)} emails.")

        for index, email in enumerate(emails, start=1):
            print(f"\nEmail {index}")
            print("From:", email["from"])
            print("Subject:", email["subject"])
            print("Date:", email["date"])
            print("Snippet:", email["snippet"][:150])

    except GmailConnectionError as exc:
        print("\nGMAIL CONNECTION FAILED")
        print(str(exc))


if __name__ == "__main__":
    main()
