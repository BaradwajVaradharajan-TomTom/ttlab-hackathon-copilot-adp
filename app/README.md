# Vandalism Hackathon


## Genie CLI

A python CLI tool to interact with the Genie API via the command line.

### Installation

Run `poetry install` from inside `backend` directory
Once installed you can `genie` in your command prompt and see the help message. That means the CLI is installed correctly.

### How to use
Before you start using the CLI tool you need to create your personal Genie space inside a Databricks workspace and also
a personal access token for the same workspace. See the official [Genie documentation](https://learn.microsoft.com/en-us/azure/databricks/genie/conversation-api#create-test) for more details, if in doubt.

Once you have your Genie space id and personal access token, add them to the `.env` file in the `backend` directory,
together with the `DATABRICKS_SERVER_HOSTNAME`

```dotenv
DATABRICKS_SERVER_HOSTNAME=https://adb-1107515897294364.4.azuredatabricks.net
DATABRICKS_HTTP_PATH=your-http-path
DATABRICKS_TOKEN=your-personal-access-token
DATABRICKS_CATALOG=your-catalog
DATABRICKS_SCHEMA=your-schema
DATABRICKS_GENIE_SPACE_ID=your-genie-space-id
```
Ignore the `DATABRICKS_HTTP_PATH`, `DATABRICKS_CATALOG` and `DATABRICKS_SCHEMA`. Genie doesn't need them!

Congratulations, you are now ready to have a conversation with Genie. 

Genie works with conversations, with each conversation being able to maintain context, hence there are two ways to interact with Genie:

#### Start a new conversation 
This will start a new conversation based on your first question and it works like this:

```bash
  genie start -q "Hi Genie, what are the changesets in Greece for the last month?"
```

#### Follow up on an existing conversation
This will continue the conversation based on the previous context and works like this:

```bash
  genie followup -q "Can you now do the same for Netherlands?"
```

When running the `followup` command, Genie will automatically continue on the last conversation you had with it. It 
knows which one was the last because it stores its id in the `.genie_session.json` file in the `backend` directory, 
when you run the `start` command.

If you want to use a different conversation, you can specify the conversation id with the `-c` flag like this:

```bash
  genie followup -q "Can you remind what was the last thing I asked you in this conversation" -c <conversation-id>
```

or manually paste this in the `.genie_session.json` file directly. If the conversation id is invalid, because that 
conversation is deleted for example, you will get an error message. 

In case a convesation id exists in the `.genie_session.json` file, but you also provide it via the CLI using the `-c` 
flag, CLI id will take precedence and the one in the file will be ignored.

