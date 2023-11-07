import os
from pdf2docx import Converter
from mammoth import convert_to_html

class pdf2html:
    def __init__(self):pass

    def convert_pdf_to_docx_and_html(self,pdf_path, output_directory):
        # Extract the file name without extension
        file_name = os.path.splitext(os.path.basename(pdf_path))[0]

        # Path for the common output directory
        common_output_directory = output_directory
        os.makedirs(common_output_directory, exist_ok=True)

        # Path for the DOCX output file
        docx_directory = os.path.join(common_output_directory, "docs")
        os.makedirs(docx_directory, exist_ok=True)
        docx_path = os.path.join(docx_directory, f'{file_name}.docx')

        # Convert the PDF to DOCX
        cv = Converter(pdf_path)
        cv.convert(docx_path, start=0, end=None)
        cv.close()

        # Path for the HTML output file
        html_directory = os.path.join(common_output_directory, "html")
        os.makedirs(html_directory, exist_ok=True)
        html_path = os.path.join(html_directory, f'{file_name}.html')

        # Define the conversion options (you can customize these)
        convert_options = {
            "ignore_empty_paragraphs": True,
        }

        # Convert DOCX to HTML
        with open(docx_path, "rb") as docx_file:
            result = convert_to_html(docx_file)

        # Save the HTML to a file
        with open(html_path, "w", encoding="utf-8") as html_file:
            html_file.write(result.value)

        return docx_path,html_path