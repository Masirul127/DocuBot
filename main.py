from fastapi import FastAPI, UploadFile,File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from numpy.lib.type_check import imag
from pydantic import BaseModel
from enum import Enum
from typing import Dict, List, Optional
import logging 
import os
from pdf_html import pdf2html


app = FastAPI(debug=True,
              docs_url='/cnvrt/docs',
              redoc_url='/cnvrt/redoc',
              openapi_url='/cnvrt/openapi.json')


#log.basicConfig(filename='logs/cv-api.log', level=log.DEBUG,
                    #format='%(asctime)s:%(levelname)s:%(message)s')

UPLOAD_FOLDER = 'uploads'
STATIC_FOLDER = 'static/results'

isdir = os.path.isdir(UPLOAD_FOLDER)
if not isdir:
    os.makedirs(UPLOAD_FOLDER)

isdir = os.path.isdir(STATIC_FOLDER)
if not isdir:
    os.makedirs(STATIC_FOLDER)



origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

convrt = pdf2html()

class ExtractResult(BaseModel):
    docx_path:Optional[str]
    html_path: Optional[str]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.docx_path = kwargs.get('docx_path')
        self.html_path = kwargs.get('html_path')

@app.get('/', include_in_schema=False)
def index():
    return RedirectResponse('cnvrt/docs')

@app.post('/convert/pdf', tags=['docu'], response_model=ExtractResult)
async def extract(file: UploadFile) -> ExtractResult:
    name = file.filename.split('.')[0]
    ext = file.filename.split('.')[-1]
    pdf_path = f'{UPLOAD_FOLDER}/{name}.{ext}'
    with open(pdf_path, 'wb+') as f:
        f.write(file.file.read())
    f.close()
    docx_path,html_path = convrt.convert_pdf_to_docx_and_html(pdf_path,STATIC_FOLDER)
    result ={}
    result['docx_path'] = docx_path
    result['html_path'] = html_path
    return result
    
