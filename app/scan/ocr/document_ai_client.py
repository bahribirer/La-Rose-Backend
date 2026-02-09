import os
from google.cloud import documentai
from google.api_core.client_options import ClientOptions
from google.oauth2 import service_account

PROJECT_ID = "548043448414"
LOCATION = "us"
PROCESSOR_ID = "d9cefd8bf7d33096" # Custom Trained Processor (v2)

# Explicitly load Document AI credentials (firebase.py overrides GOOGLE_APPLICATION_CREDENTIALS)
_DOCAI_CREDS_PATH = os.environ.get("DOCAI_CREDENTIALS_PATH") or "/home/ec2-user/creds/google.json"
_DOCAI_CREDENTIALS = service_account.Credentials.from_service_account_file(_DOCAI_CREDS_PATH)


def process_document(file_path: str):
    opts = ClientOptions(
        api_endpoint=f"{LOCATION}-documentai.googleapis.com"
    )

    client = documentai.DocumentProcessorServiceClient(
        client_options=opts,
        credentials=_DOCAI_CREDENTIALS,
    )

    name = client.processor_path(
        PROJECT_ID, LOCATION, PROCESSOR_ID
    )

    with open(file_path, "rb") as f:
        content = f.read()

    raw_document = documentai.RawDocument(
        content=content,
        mime_type="application/pdf"
        if file_path.endswith(".pdf")
        else "image/jpeg"
    )

    request = documentai.ProcessRequest(
        name=name,
        raw_document=raw_document
    )

    result = client.process_document(request=request)
    return result.document
