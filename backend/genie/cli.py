import argparse
import os
import sys

from colorama import Fore
from dotenv import load_dotenv

from .genie_client import GenieClient


def main():
    parser = argparse.ArgumentParser(
        description="Databricks Genie CLI – Start and follow up on Genie conversations."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Start a new Genie conversation")
    start_parser.add_argument("--question", "-q", help="Initial question to ask Genie")

    follow_parser = subparsers.add_parser("followup", help="Ask a follow-up question")
    follow_parser.add_argument(
        "--question", "-q", required=True, help="Follow-up question"
    )
    follow_parser.add_argument("--conv_id", "-c", help="Conversation ID")

    args = parser.parse_args()
    load_dotenv()
    client = GenieClient(
        workspace_url=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        auth_token=os.getenv("DATABRICKS_TOKEN"),
        space_id=os.getenv("DATABRICKS_GENIE_SPACE_ID"),
    )

    if args.command == "start":
        if not args.question:
            print(
                Fore.YELLOW
                + "⚠️ Please provide a question to start the conversation."
                + Fore.RESET
            )
            sys.exit(1)
        print(Fore.YELLOW + f"🟢 Starting conversation:{Fore.RESET}`{args.question}`" )
        conv = client.start_conversation(args.question)
        conversation_id = conv["conversation_id"]
        message_id = conv["message_id"]
        client.save_session(conversation_id)
        message = client.wait_for_completion(conversation_id, message_id)
        client.print_response(message)

    elif args.command == "followup":
        if args.conv_id:
            conversation_id = args.conv_id
            print(
                Fore.YELLOW
                + f"\n🔄 Continuing conversation with ID: {Fore.RESET}{conversation_id}"
            )
        elif session := client.load_session():
            conversation_id = session["conversation_id"]
            print(
                Fore.YELLOW
                + f"\n🔄 Resuming conversation id: {Fore.RESET}{conversation_id} {Fore.YELLOW}from session file: {Fore.RESET}`{client.SESSION_FILE_PATH}`"
            )
        else:
            print(
                Fore.YELLOW
                + f"\n⚠️ Please provide a valid conversation id via {Fore.RESET}`{client.SESSION_FILE_PATH}`{Fore.YELLOW} or via CLI!"
                + Fore.RESET
            )
            sys.exit(1)

        print(Fore.YELLOW + f"🔁 Asking follow-up: {Fore.RESET}`{args.question}`")
        follow_up = client.ask_follow_up(conversation_id, args.question)
        message = client.wait_for_completion(conversation_id, follow_up["message_id"])
        client.print_response(message)
        client.save_session(conversation_id)


if __name__ == "__main__":
    main()
