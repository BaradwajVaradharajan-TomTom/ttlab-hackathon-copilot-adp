import json
import os
import re
import sys
import time
from time import sleep
from typing import Optional

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

    def get_message_result(self, message: dict) -> dict | None:
        match message["status"]:
            case "COMPLETED":
                for attachment in message["attachments"]:
                    if "text" in attachment.keys():
                        return {"type":"text", "message": attachment['text']['content']}
                    elif "query" in attachment.keys():
                        return {"type":"query", "message": attachment['query']['query']}
                    else:
                        print("unknown entity in the message[status]")
                                
            case "FAILED":
                print(Fore.RED + "\n⚠️ Genie response failed!" + Fore.RESET)
            case "CANCELLED":
                print(Fore.RED + "\n⚠️ Genie conversation was cancelled!" + Fore.RESET)
            case _:
                print(
                    Fore.RED + "\n⚠️ Unexpected Genie response status:" + Fore.RESET,
                    message["status"],
                )
 


    def ask_question(self, question: str, conversation_id: Optional[str] = None) -> dict:
        """
        Sends a message to a Databricks Genie conversation.

        Parameters:
        - conversation_id (str): Genie conversation ID
        - question (str): The message/question to send to Genie

        Returns:
        - dict: JSON response from the Genie API
        """
        if not conversation_id:
            conversation = self.start_conversation(question)
            conversation_id = conversation["conversation_id"]
            message_id = conversation["message_id"]
            completed_message = self.wait_for_completion(conversation_id, message_id)
            return self.get_message_result(completed_message)
        else:
            message_id = self.ask_follow_up(conversation_id, question)["message_id"]
            completed_message = self.wait_for_completion(conversation_id, message_id)
            return self.get_message_result(completed_message)

    def execute_sql_query(self, warehouse_id: str, query: str, timeout_seconds: int = 50) -> dict:
        """
        Execute a SQL query on a Databricks SQL warehouse and return the results.
        
        Args:
            warehouse_id: The ID of the SQL warehouse to execute the query on
            query: The SQL query to execute
            timeout_seconds: Maximum time to wait for query completion in seconds
            
        Returns:
            A dictionary containing:
            - manifest: The query result schema and metadata
            - data_array: List of rows from the query result
            
        Raises:
            Exception: If the query fails or times out
        """
        # Endpoint for statement execution
        url = f"{self.workspace_url}/api/2.0/sql/statements/"
        
        # Prepare the request payload
        payload = {
            "statement": query,
            "warehouse_id": warehouse_id,
            "wait_timeout": f"{timeout_seconds}s",
            "disposition": "INLINE",
            "format": "JSON_ARRAY",
            "on_wait_timeout": "CANCEL"
        }
        
        try:
            # Execute the statement
            response = requests.post(
                url=url,
                headers=self.headers,
                json=payload,
                timeout=timeout_seconds+1  # Connection timeout in seconds
            )
            response.raise_for_status()
            
            # Get the statement ID and initial status
            statement = response.json()
            statement_id = statement["statement_id"]
            status = statement["status"]
            
            # Poll for completion
            start_time = time.time()
            status_response = None
            while status["state"] in ("PENDING", "RUNNING"):
                # Check for timeout
                if time.time() - start_time > timeout_seconds:
                    raise TimeoutError(f"Query execution timed out after {timeout_seconds} seconds")
                
                # Wait before polling again
                time.sleep(1)
                
                # Check statement status
                status_url = f"{url}{statement_id}"
                status_response = requests.get(
                    url=status_url,
                    headers=self.headers,
                    timeout=timeout_seconds+1
                )
                status_response.raise_for_status()
                
                status = status_response.json()["status"]
                if status["state"] == "SUCCEEDED":
                    break
                elif status["state"] == "FAILED":
                    error_message = status.get("error", {}).get("message", "Unknown error")
                    raise Exception(f"Query execution failed: {error_message}")
                elif status["state"] == "CANCELED":
                    raise Exception("Query execution was canceled")
            
            response_data = status_response.json() if status_response else statement
            
            if status['state'] == 'SUCCEEDED':
                # Return both manifest and data_array for the query result
                return {
                    "manifest": response_data.get("manifest", {}),
                    "data_array": response_data.get("result", {}).get("data_array", [])
                }
            return {"manifest": {}, "data_array": []}
            
        except requests.exceptions.RequestException as e:
            error_message = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    error_message = f"{error_message}: {error_details}"
                except:
                    pass
            raise Exception(f"Failed to execute query: {error_message}")


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

    def get_query_result(self, conversation_id: str, message_id: str, attachment_id: str) -> dict:
        """
        Get the result of a SQL query attachment.
        
        Args:
            conversation_id: The ID of the conversation
            message_id: The ID of the message containing the query
            attachment_id: The ID of the query attachment
            
        Returns:
            Dictionary containing the query result
        """
        url = (
            f"{self.workspace_url}/api/2.0/genie/spaces/{self.space_id}/"
            f"conversations/{conversation_id}/messages/{message_id}/"
            f"attachments/{attachment_id}/query-result"
        )
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def print_response(self, message: dict, conversation_id: str = None, message_id: str = None):
        """
        Print the response from Genie, including query results if available.
        
        Args:
            message: The message response from Genie
            conversation_id: The ID of the conversation (required for fetching query results)
            message_id: The ID of the message (required for fetching query results)
        """
        match message["status"]:
            case "COMPLETED":
                for attachment in message["attachments"]:
                    if "text" in attachment.keys():
                        print(
                            Fore.GREEN
                            + f"\n\nResponse: {Fore.RESET} \n{attachment['text']['content']}"
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
                        
                        print(Fore.LIGHTRED_EX + f"\n\nQuery: {attachment['query']}" + Fore.RESET)

                        # If we have the required IDs, fetch and display query results
                        if conversation_id and message_id and "attachment_id" in attachment["query"]:
                            try:
                                result = self.get_query_result(
                                    conversation_id=conversation_id,
                                    message_id=message_id,
                                    attachment_id=attachment["query"]["attachment_id"]
                                )
                                print(
                                    Fore.GREEN
                                    + f"\n\nQuery Results: {Fore.RESET} \n{json.dumps(result, indent=2)}"
                                )
                            except Exception as e:
                                print(
                                    Fore.RED
                                    + f"\n⚠️ Failed to fetch query results: {Fore.RESET}{str(e)}"
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
