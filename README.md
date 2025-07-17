## Property‑Manager Email (AI Powered) Assistant:

This Python service connects to an email inbo, process unread emails using an LLM, creates any relevent action items and sends a repsonse back to the relevant stakeholders.

## Set up

## Installing Poetry

I used poetry which is a python dependency manager. To install poetry please refer to the docs provided below:
https://python-poetry.org/docs/

If you have pipx you can run

```bash
pipx install poetry
```

or using the official installer

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

## Installing dependencies

Once poetry is installed you can install the dependencies with the falling command

Activate the virtual environment:

```python
poetry shell
```

Install dependencies:

```python
poetry install
```

# Setting up an email inbox

For demoing this project I reccommend using a gmail account, as this is what was used for developmenet and testing.

Once a gmail account is created go to the settings tab and ensure that IMAP is enabled

Go to **Manage account settings** and under the security tab ensure that **2-step verification is enabled**

Search for App passwords in the nav bar and create a new app password. Ensure you save this as it will be used an an environment variable.

# Configuring environement variables

Create a .env file in the directory

The following environment variables are needed:

```
HOST (set this to imap.gmail.com)
USERNAME (set this to your email address that was created)
PASSWORD (set this to the App password that was created in the previous step)
OPEN_AI_KEY (set this to your OPEN AI API key)
```

## Running the program

To run the program, ensure that there are unread emails in the email address referred in the .env file

```python
poetry run python main.py
```

The program should parse through the emails, generate a response and any relevant action items, and save them as json files on the disk.

## Assumptions made

Some of the assumptions I made while building this assistant was the number of possible requests a tenant could have. I broke it down to either maintainence issues, payment inquires, lease information or a general inquiry if none of the above matched.

For simplicity all data is randomly generated using the faker library. I also assumed the tenant will always receive an email response per email they send as well. If a tenant explicitly states that they do not want a response, the service does not currently take that into account.

## Limitations and possible improvements

While I did incorporate some basic error handeling when replying back to customer's emails failures could occur at other parts of the process, notablly when processing an unread email and generating a reply.

While I did incorporate a fallback rule-based parser if the LLM failed to parse the email correctly, this is a relatively bare bones implementation, and ideally a possible improvement would be to retry parsing the message with the LLM, as I found it that creating specific rules to parse and email and extract it's context was quite a nuanced process.

The major risk of an email failing to be parsed or generating a response is that we mark the email as unread when we initially go through all unread emails in an inbox. This means our service will not reprocess this email if we attempt to retry and the tenant will not receive a reponse, and an action item will not be generated.

A way to improve this would be
