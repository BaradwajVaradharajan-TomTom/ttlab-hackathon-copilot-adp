import json
import os
import re
import sys
from time import sleep

import requests
from colorama import Fore


class GenieClient:
    SESSION_FILE_PATH = ".genie_session.json"

    def __init__(self, workspace_url: str, auth_token: str, space_id: str):
        """
        Initializes the Genie client.
        :param workspace_url: Your Databricks instance URL (e.g., 'https://abc.cloud.databricks.com')
        :param auth_token: Your personal access token for authentication
        """
        self.workspace_url = workspace_url
        self.auth_token = auth_token
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }
        self.space_id = space_id

    def wait_for_completion(self, conversation_id: str, message_id: str) -> dict | None:
        while True:
            message = self.get_message(conversation_id, message_id)
            status = message["status"]
            sys.stdout.write(
                Fore.YELLOW
                + f"\r\033[K⏳ Waiting for response, status: {Fore.RESET}{status}"
            )
            sys.stdout.flush()
            if status in ("COMPLETED", "FAILED", "CANCELLED"):
                return message
            sleep(3)

    def start_conversation(self, question: str) -> dict:
        """
        Start a conversation with Databricks Genie space.

        Args:
            question: The content/question to send

        Returns:
            A dictionary with the response JSON
        """
        url = f"{self.workspace_url}/api/2.0/genie/spaces/{self.space_id}/start-conversation"
        payload = {"content": question}
        response = requests.post(url=url, headers=self.headers, json=payload)
        response.raise_for_status()  # Raise exception for HTTP errors
        return response.json()

    def get_message(self, conversation_id: str, message_id: str) -> dict:
        """
        Retrieve a specific message from a Databricks Genie conversation.

        Args:
            conversation_id: The ID of the conversation
            message_id: The ID of the message

        Returns:
            A dictionary with the response JSON
        """
        url = (
            f"{self.workspace_url}/api/2.0/genie/spaces/"
            f"{self.space_id}/conversations/{conversation_id}/messages/{message_id}"
        )

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()  # Raise exception on HTTP errors
        return response.json()

    def ask_follow_up(self, conversation_id: str, question: str) -> dict:
        """
        Sends a message to a Databricks Genie conversation.

        Parameters:
        - conversation_id (str): Genie conversation ID
        - question (str): The message/question to send to Genie

        Returns:
        - dict: JSON response from the Genie API
        """
        url = f"{self.workspace_url}/api/2.0/genie/spaces/{self.space_id}/conversations/{conversation_id}/messages"
        payload = {"content": question}
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()  # Raise error for bad responses
        return response.json()

    def save_session(self, conversation_id: str):
        with open(self.SESSION_FILE_PATH, "w") as f:
            json.dump({"conversation_id": conversation_id}, f)

    def load_session(self):
        if os.path.exists(self.SESSION_FILE_PATH):
            with open(self.SESSION_FILE_PATH) as f:
                return json.load(f)
        return None

    def print_response(self, message: dict):
        match message["status"]:
            case "COMPLETED":
                for attachment in message["attachments"]:
                    if "text" in attachment.keys():
                        print(
                            Fore.GREEN
                            + f"\n\nResponse: {Fore.RESET} \n{attachment["text"]["content"]}"
                        )
                    elif "query" in attachment.keys():
                        print(
                            Fore.GREEN
                            + f"\n\nQuery description: {Fore.RESET} \n{attachment['query']['description']}"
                        )
                        print(
                            Fore.GREEN
                            + f"\nSQL query: {Fore.RESET} \n{self.pretty_print_sql_(attachment['query']['query'])}"
                        )
                        print(
                            Fore.GREEN
                            + f"\nQuery metadata: {Fore.RESET} \n{attachment['query']['query_result_metadata']}"
                        )
            case "FAILED":
                print(Fore.RED + "\n⚠️ Genie response failed!" + Fore.RESET)
            case "CANCELLED":
                print(Fore.RED + "\n⚠️ Genie conversation was cancelled!" + Fore.RESET)
            case _:
                print(
                    Fore.RED + "\n⚠️ Unexpected Genie response status:" + Fore.RESET,
                    message["status"],
                )

    @staticmethod
    def pretty_print_sql_(sql: str) -> str:
        # List of common SQL keywords
        keywords = [
            "SELECT",
            "FROM",
            "WHERE",
            "JOIN",
            "INNER JOIN",
            "LEFT JOIN",
            "RIGHT JOIN",
            "FULL JOIN",
            "GROUP BY",
            "ORDER BY",
            "HAVING",
            "LIMIT",
            "OFFSET",
            "UNION",
            "AND",
            "OR",
            "ON",
            "IN",
            "AS",
            "DISTINCT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "VALUES",
            "SET",
            "INTO",
        ]

        # Regex pattern to match whole word SQL keywords
        pattern = r"\b(" + "|".join(re.escape(kw) for kw in keywords) + r")\b"

        # Insert newline before matched keyword
        return re.sub(pattern, r"\n\1", sql)
