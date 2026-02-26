import os
import time
from xml.sax.saxutils import escape
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import Response
from twilio.request_validator import RequestValidator
from starlette.concurrency import run_in_threadpool

from app.api.schemas import HoneypotRequest
from app.core.orchestrator import handle_event

router = APIRouter(prefix="/integrations/twilio", tags=["twilio"])

@router.post("/inbound")
async def twilio_inbound(request: Request):
    """
    Twilio inbound webhook. Validates X-Twilio-Signature and returns inline TwiML.
    """
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not auth_token:
        raise HTTPException(status_code=403, detail="Twilio auth token not configured")
        
    validator = RequestValidator(auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")
    
    # Read the form data
    form_data = await request.form()
    post_vars = {k: v for k, v in form_data.items()}
    
    # Twilio validator uses the full URL including scheme and host
    url = str(request.url)
    
    if not validator.validate(url, post_vars, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
        
    from_number = post_vars.get("From", "")
    to_number = post_vars.get("To", "")
    body = post_vars.get("Body", "")
    message_sid = post_vars.get("MessageSid", "")
    
    channel = "WhatsApp" if from_number.startswith("whatsapp:") else "SMS"
    
    # Build canonical request
    req_data = {
        "sessionId": f"twilio:{from_number}",
        "message": {
            "sender": "scammer",
            "text": body,
            "timestamp": int(time.time() * 1000)
        },
        "conversationHistory": [],
        "metadata": {
            "channel": channel,
            "provider": "Twilio",
            "to": to_number,
            "messageSid": message_sid
        }
    }
    
    req = HoneypotRequest(**req_data)
    
    # Call the orchestrator
    out = await run_in_threadpool(handle_event, req)
    
    # Extract reply
    reply_val = ""
    if isinstance(out, tuple) and len(out) == 1:
        out = out[0]
    if isinstance(out, dict):
        reply_val = out.get("reply") or ""
    elif isinstance(out, str):
        reply_val = out
    else:
        reply_val = str(out)
        
    # Escape the reply text for XML
    escaped_reply = escape(reply_val)
        
    # Construct real XML TwiML
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{escaped_reply}</Message>
</Response>"""

    return Response(content=twiml, media_type="text/xml")
