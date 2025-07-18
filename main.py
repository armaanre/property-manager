import os
from context_loader import ContextLoader
from inbox import InboxConnector
from parser import LLMEmailParser
from dotenv import load_dotenv
from workflow import WorkflowTrigger
from reply_generator import ReplyGenerator
from sender import EmailSender




if __name__ == "__main__":
    load_dotenv()
    connector = InboxConnector(
        host="imap.gmail.com",
        username=os.environ.get("USERNAME"),
        password=os.environ.get("PASSWORD"),
    )
    connector.connect()
    new_msgs = connector.fetch_unread(limit=5)
    
    
    parser     = LLMEmailParser(model="gpt-4o-mini")
    ctx_loader = ContextLoader(seed=42)
    replier    = ReplyGenerator(model="gpt-4o-mini")
    workflow  = WorkflowTrigger(output_dir="action_items")
    
    email_sender = EmailSender(
        smtp_host="smtp.gmail.com",
        smtp_port=465,
        username=os.environ.get("USERNAME"),
        password=os.environ.get("PASSWORD"),
        max_retries=3,
        retry_delay=2.0    )

    
    for msg in new_msgs:
        parsed_dict = parser.parse(msg) 
        context = ctx_loader.load(parsed_dict["tenant_name"], parsed_dict["address"])
        ticket_id = workflow.process(parsed_dict, context)  
        reply   = replier.generate(parsed_dict, context, ticket_id)
        
        tenant_email = msg["sender"]
        subject = f"Re: {msg['subject']}"

        email_sender.send_email(
            to=[tenant_email],
            subject=subject,
            body=reply,
        )

    
    connector.logout()