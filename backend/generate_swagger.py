#!/usr/bin/env python3
"""Generate OpenAPI/Swagger specification file"""

import json
from app import app

def generate_openapi_spec(output_file: str = "openapi.json"):
    """Generate and save OpenAPI specification to a file"""
    openapi_schema = app.openapi()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    
    print(f"OpenAPI specification generated: {output_file}")
    return openapi_schema

if __name__ == "__main__":
    generate_openapi_spec()

