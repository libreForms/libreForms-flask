""" 
pdf.py: generate PDFs from various data sources

# Skel

The `skel` is the skeleton of the form that may contain fields
that are not included in the form object `data_structure`; likewise,
the form object `data_structure` may contain metadata fields not 
included in the `skel`. So by passing a skel, you may get a form with 
some of its fields left unfilled. This is the starting place for 
more consistent PDF forms structures. For more information, see
https://github.com/libreForms/libreForms-flask/issues/133.


"""

__name__ = "app.pdf"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "2.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.scripts import convert_to_string

def generate_pdf(   
                    form_name:str, 
                    data_structure, 
                    username,
                    skel=None,
                    document_name=None, 
                    encrypt=None):

    # if the user doesn't pass their own document name, create one
    if not document_name: 
        document_name= f'{datetime.datetime.utcnow().strftime("%Y-%m-%d")}_{username}_{form_name}.pdf'


    doc = SimpleDocTemplate(document_name, pagesize=letter, rightMargin=30,
                            leftMargin=30, topMargin=30, bottomMargin=18)
    
    elements = []

    data = []

    # Here we implement `skel` support, see discussion at
    # https://github.com/libreForms/libreForms-flask/issues/133.
    if skel:
        for key, value in skel.items():

            # In the future, we may need to add add'l checks here, like
            # verifying depends_on or deny_access data. But for now, we 
            # only add a skeleton 

            if key in data_structure.keys(): 
                if isinstance(value, list):
                    data.append([key.replace('_'," "), str(data_structure[key])])
                elif isinstance(value, dict):
                    data.append([key.replace('_'," "), str(data_structure[key])])
                else:
                    data.append([key.replace('_'," "), str(data_structure[key])])


        for key, value in data_structure.items():
            if key not in skel.keys():
                if isinstance(value, list):
                    data.append([key.replace('_'," "), str(value)])
                elif isinstance(value, dict):
                    data.append([key.replace('_'," "), str(value)])
                else:
                    data.append([key.replace('_'," "), str(value)])
        

        # This approach adds add'l rows of data with descriptions
        # We really should add a page break here (https://stackoverflow.com/a/23423035/13301284) 
        # ... or else integrate this element as a third column directly beside the corresponding
        # value above...
        data.append(["Descriptions"])
        for key, value in skel.items():
            # print(skel[key])
            # print(skel[key].keys())
            if 'description' in skel[key]['output_data'].keys():
                data.append([key.replace('_'," "), str(skel[key]['output_data']['description'])])




    # This script generates a basic PDF and puts values into a 
    # table after converting them to a list {key:value, key2:value2} > 
    # [[key,value][key,value]] but it doesn't create a header (like, 
    # a page title), nor can it handle more complex data structures 
    # like 
        # {key:[value1, value2]} > ? 
    # or 
        # {key:{child_key1:child_value1, child_key2:child_value2}} > ?
    # See https://github.com/signebedi/libreForms/issues/53.
    else:
        for key, value in data_structure.items():


                # this is placeholder logic to eventually handle different
                # data structures, eg. by creatine multiple columns (for 
                # lists) or creating add'l rows (for each dict item). The
                # only thought I have is that there may be some customization
                # that admins may want to be able to define slightly different
                # behavior; my contention is that this would occur generally in
                # the scope of the output data type specified by the form config.
                if isinstance(value, list):
                    data.append([key.replace('_'," "), str(value)])
                elif isinstance(value, dict):
                    data.append([key.replace('_'," "), str(value)])
                else:
                    data.append([key.replace('_'," "), str(value)])
        
    # print(data)


    # PLACEHOLDER - iterate through each form field in the form config / skel
    # and verify eg. whether `_depends_on` and `_deny_group` apply to each field;
    # also determine whether there is a description and, if so, include the form and
    # each corresponding form-field description provided.

    # # https://stackoverflow.com/questions/3372885/how-to-make-a-simple-table-in-reportlab
    # table = Table(data, colWidths=270, rowHeights=79)
    # elements.append(table)
    # doc.build(elements) 
    
    # https://zewaren.net/reportlab.html
    style = TableStyle([
                        ('ALIGN',(1,1),(-2,-2),'RIGHT'),
                        # ('TEXTCOLOR',(1,1),(-2,-2),colors.red),
                        ('VALIGN',(0,0),(0,-1),'TOP'),
                        # ('TEXTCOLOR',(0,0),(0,-1),colors.blue),
                        ('ALIGN',(0,-1),(-1,-1),'CENTER'),
                        ('VALIGN',(0,-1),(-1,-1),'MIDDLE'),
                        # ('TEXTCOLOR',(0,-1),(-1,-1),colors.green),
                        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                        ])

    # Configure style and word wrap
    s = getSampleStyleSheet()
    s = s["BodyText"]
    s.wordWrap = 'CJK'
    data2 = [[Paragraph(cell, s) for cell in row] for row in data]
    t=Table(data2)
    t.setStyle(style)

    # Send the data and build the file
    elements.append(t)
    doc.build(elements)



def calculate_field_position(total_fields, current_field, page_height):
    # Define the position of the top of the first field
    first_field_y = page_height - 100

    # Calculate the vertical distance between each field
    field_spacing = 20

    # Calculate the position of the current field
    current_field_y = first_field_y - current_field * field_spacing

    # Return the position as a tuple
    return (100, current_field_y)


# def convert_to_string(data):
#     if isinstance(data, list):
#         # Convert each item in the list to a string and join them with commas
#         return ", ".join(str(item) for item in data)
#     elif isinstance(data, dict):
#         # Convert each key-value pair in the dictionary to a string and join them with commas
#         return ", ".join(f"{key}: {value}" for key, value in data.items())
#     # Return the input as a string
#     return str(data)

def add_border(canvas):
    """Adds a 1px black border around the current canvas"""
    canvas.setStrokeColorRGB(0, 0, 0)
    text_width, text_height = canvas.stringWidth(str(canvas._code)), canvas._leading
    x, y = canvas._x, canvas._y
    width, height = text_width + 2, text_height + 2
    canvas.rect(x, y, width, height, stroke=1, fill=0)
    return canvas

def v2_generate_pdf(   form_name:str, 
                        data_structure:dict, 
                        document_id:str,
                        document_name=None):

    # 64068a5d03728ef3a5f3e765

    # if the user doesn't pass their own document name, create one
    if not document_name: 
        document_name= f'{datetime.datetime.utcnow().strftime("%Y-%m-%d")}_{form_name}_{document_id}.pdf'

    # Calculate the total number of fields
    total_fields = len(data_structure)

    # Create a new PDF document
    pdf_canvas = canvas.Canvas(document_name, pagesize=letter)

    # Set the font for the document
    pdf_canvas.setFont("Helvetica", 10)

    # Total dictionary of positions
    field_position_dict = {}

    # Iterate over the form field names, and draw them on the page
    for i, field in enumerate(data_structure.keys()):
        response = convert_to_string(data_structure[field])
        field_name = field[1:].replace('_', ' ') if field.startswith('_') else field.replace('_', ' ')
        position = calculate_field_position(total_fields, i, letter[1])
        field_position_dict[field] = position # add position to the total dictionary of positions
        pdf_canvas.drawString(position[0], position[1], field_name)
        pdf_canvas.drawString(position[0] + 100, position[1], response)

    # print(field_position_dict)

    # for response, position in zip([convert_to_string(x) for x in data_structure.values()], field_position_dict.values()):
    #     # print(position)
    #     pdf_canvas.drawString(position[0], position[1], response)
    #     pdf_canvas = add_border(pdf_canvas)


    # Save the PDF document and close the canvas
    pdf_canvas.save()

def v3_generate_pdf(    form_name:str, 
                        form_data:dict,
                        metadata:dict,
                        document_id:str,
                        document_name=None,
                        **kwargs):
    
    # if the user doesn't pass their own document name, create one
    if not document_name: 
        document_name= f"{form_name}_{document_id}.pdf"


    # Define the table data
    data = [ [key,convert_to_string(value)] for key,value in form_data.items()]

    # data = [
    #     ["a", ""],
    #     ["b", ""],
    #     ["c", ""],
    #     ["d", ""],
    #     ["e", ""],
    #     ["f", ""],
    #     ["g", ""],
    #     ["h", ""]
    # ]

    # # Define data
    # form_name = "request"
    # doc_id = "asjd832-aasd2"
    # date = "10-Mar-23"

    # Define the table style
    style = TableStyle([
        # ("BACKGROUND", (0, 0), (-1, 0), colors.white),
        # ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        # ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        # ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        # ("FONTSIZE", (0, 0), (-1, 0), 10),
        # ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        # # ("LEFTPADDING", (0, 0), (-1, 0), 10),
        # ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        # ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (0, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (0, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BOX", (0, 0), (-1, -1), 1, colors.black)
    ])

    # Define the table dimensions, cell height and column widths
    cell_height = 50
    data_len = len(data)
    table_height = data_len * cell_height
    table_width = 8.5 * inch
    table = Table(data, colWidths=[2.33 * inch, 4.67 * inch], rowHeights=[cell_height] * data_len, style=style, hAlign="LEFT")

    # Define the header style and content
    header_style = ParagraphStyle(name="Header", fontName="Helvetica-Bold", fontSize=14, alignment=0, leftIndent=10, textColor=colors.black)
    form_name = Paragraph(form_name, header_style)

    right_style = ParagraphStyle(name="right_style", fontSize=10, alignment=2, rightIndent=10)
    document_id = Paragraph(f"Document ID: {document_id}", right_style)
    date = Paragraph(f"Date: {datetime.datetime.utcnow().strftime('%Y-%m-%d')}", right_style)

    # Build the document with the header and table
    doc = SimpleDocTemplate(document_name, pagesize=letter, leftMargin=10, rightMargin=10, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    elements = [form_name, document_id, date, Paragraph("<br/><br/>", header_style), table ]
    doc.build(elements)


if __name__=="__main__":
    data = {'Description': 'This project requests approval for $3 million over seven '
                'years to develop a turnip GMO with significantly increased '
                'nutritional value.',
            'Existing_Request': 'No',
            'Job_Number': '23854',
            'Mission_Team': 'Special Projects (SP)',
            'Owner': 'John Smith (smithj22@example.com)',
            'Reporter': 'smithj22',
            'Risk_Level': 'medium',
            'Select': ['1'],
            'Shortname': 'Nutritional Value of Turnips',
            'Start_Date': '2022-12-29',
            'Timestamp': '2022-11-27 15:03:00.949681',
            '_id': '63837c241cc1c836267a4c24'}
    
    print (data)
    
    generate_pdf('status', data, '')