from agentic_doc.parse import parse_documents

def get_parsed_doc_from_landingai(file_url: str):
    try:
        results = parse_documents([file_url])
        return results[0]
    except Exception as e:
        raise Exception(str(e),"Document processing failed : No results returned")
    
