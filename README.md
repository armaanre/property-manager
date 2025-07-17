## Property‑Manager Email (AI Powered) Assistant:

This Python service connects to an email inbox, process unread emails using an LLM, creates any relevent action items and sends a repsonse back to the relevant stakeholders.

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

# Assumptions made

Some of the assumptions I made while building this assistant was the number of possible requests a tenant could have. I broke it down to either maintenance issues, payment inquires, lease information or a general inquiry if none of the above matched. In addition the only support available right now is English, so we assume all our tenants can communicate in English.

For simplicity all data is randomly generated using the faker library. I also assumed the tenant will always receive an email response per email they send as well. If a tenant explicitly states that they do not want a response, the service does not currently take that into account.

## Limitations and possible improvements

While I did incorporate some basic error handling when replying back to customer's emails failures could occur at other parts of the process, notablly when processing an unread email and generating a reply.

While I did incorporate a fallback rule-based parser if the LLM failed to parse the email correctly, this is a relatively bare bones implementation, and ideally a possible improvement would be to retry parsing the message with the LLM, as I found it that creating specific rules to parse and email and extract it's context was quite a nuanced process.

A possible enhancement to the json tickets created would also be a priority label, as some actions are more urgent than others. SLA's could also be defined for the asignee of these tickets. I did ensure the id of the ticket was sent to the customer for their reference, and a future enhancement would be to provide updates on the ticket if the customer requests for it.

The major risk of an email failing to be parsed or generating a response is that we mark the email as unread when we initially go through all unread emails in an inbox. This means our service will not reprocess this email if we attempt to retry and the tenant will not receive a response, and an action item will not be generated.

A way to improve this would be to add message queues between reading unread emails, and parsing/sending a response. This decouples our services and if we fail at any step we can add unprocessed emails to a dead letter queue to process again later, ensuring we don't ignore customer's emails.

For simplicity all the data is currently mocked. Ideally we would have a database where we would store previous customer tickets and information about their rental history. A possible index to find the relevant customer's information could be derived from their email address.

Currently this service is synchronous. If there are higher loads of emails to process this current implementation would not be feasible. Possible improvement would be to process multiple emails in parallel using a ThreadPoolExecute. Because all of our steps are I/O bound running multiple threads can help reduce latency.

To make the service more concurrent we can leverage the asyncio library to prevent any blocking tasks.

From a security stand point, an improvement would be to add a step to sanitise emails before being parsed into the LLM. Malicious users could write prompt injections via email which could lead to our service being attacked or data being leaked.

If we wanted to deploy this service, leveraging FastAPI would be an option I would consider as it's a relatively lightweight and performant web framework that supports asynchronous operations and has native Pydantic support for type safety.

From a testing stand point, currently there are only basic unit tests implemented. Writing more comprehensive tests along with integration and acceptance tests would be ideal.

Logging is also limited, and adding metrics/dashboards when deploying this service would be ideal to identify if any there are issues in a timely manner.

This service is currently leveraging OpenAI's LLM. Ideally we would like to make it LLM agnostic so we can change vendors based on the cost of tokens, and allow us to be flexible with utilising more performant LLM's for our use cases in the future.

## AI notes

From a development perspective I utilised Open AI's o4-mini-high model to help me understand the edge cases of this problem, and help me design the initial structure of this service. I also used it to help me get a better understanding of the imaplib package as I was not familiar with it.

After implementing the basic structure, and testing it e2e, I prompted the model to help me generate a better prompt for parsing and sending emails based on some of the issues I noticed in my testing. Specifically when a tenant mentions more than one possible request in an email (such as withholding payment until a maintenance request is met)

I also utilised AI to write basic unit tests based on the classes I had defined. Once my logic was complete I also generated docstrings on certain functions to provide clarity on certain logic, and as a double check to see if the AI understood what I was trying to accomplish.

While in some cases it referenced deprecated packages which I needed to correct, leveraging the model helped me from a design and testing perspective, while allowing me to implement and enhance the actual logic relatively quickly.
