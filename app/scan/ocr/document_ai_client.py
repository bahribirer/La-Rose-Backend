from google.cloud import documentai
from google.api_core.client_options import ClientOptions

PROJECT_ID = "548043448414"
LOCATION = "us"
PROCESSOR_ID = "d9cefd8bf7d33096" # Custom Trained Processor (v2)


def process_document(file_path: str):
    opts = ClientOptions(
        api_endpoint=f"{LOCATION}-documentai.googleapis.com"
    )

    client = documentai.DocumentProcessorServiceClient(
        client_options=opts
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
